#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Marstek UDP JSON client simplifié pour Jeedom.

Ce script exécute une commande unique (par défaut: all-status) et n'affiche
que la réponse JSON finale pour une intégration facile dans Jeedom.

Largement inspiré de: https://gist.github.com/slanckma/b94a6d77b81104ae441b217a669e55d7
"""

import argparse
import json
import logging
import socket
import sys
import time
from typing import Optional, Tuple, List, Any

# Suppression du logging pour ne pas polluer la sortie JSON
logging.basicConfig(level=logging.WARNING) 

DEFAULT_IP = "192.168.0.182"
DEFAULT_PORT = 30000

# Fonction hexdump conservée pour le débug
def hexdump(data: bytes) -> str:
    toprint = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hexpart = " ".join(f"{b:02x}" for b in chunk).ljust(16*3)
        asciipart = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        toprint.append(f"{i:08x}  {hexpart} |{asciipart}|")
    return "\n".join(toprint)

def make_socket(local_bind: Optional[Tuple[str, int]] = None, timeout: float = 1.5) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    if local_bind:
        s.bind(local_bind)
    else:
        # Default bind to port 30000 so Marstek replies arrive here
        s.bind(("0.0.0.0", 30000))
    return s

def send_and_receive(
    ip: str,
    port: int,
    payload: dict,
    timeout: float = 1.5,
    retries: int = 2,
    local_bind: Optional[Tuple[str, int]] = None,
) -> List[Any]:
    """Send JSON payload and collect replies, returns decoded objects."""
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sock = make_socket(local_bind=local_bind, timeout=timeout)
    addr = (ip, port)
    responses: List[Any] = []

    for attempt in range(retries + 1):
        try:
            sock.sendto(data, addr)
        except Exception as e:
            logging.error("Failed to send: %s", e)
            if attempt == retries:
                raise
            continue

        start = time.monotonic()
        while True:
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                pkt, _ = sock.recvfrom(65535)
                # Tentative de décodage JSON
                obj = json.loads(pkt.decode("utf-8", errors="strict"))
                responses.append(obj)
            except socket.timeout:
                break
            except Exception:
                # Ignorer les erreurs de décodage ou de socket silencieusement pour Jeedom
                pass

        if responses:
            break

    return responses

def execute_with_retry(
    operation_func,
    operation_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    base_timeout: float = None,
    validation_func=None
) -> Any:
    """
    Execute an operation with intelligent retry, progressive delay, and progressive timeout.

    Args:
        operation_func: Function to execute (should accept timeout parameter and return result)
        operation_name: Name of the operation for logging
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (will be doubled each attempt)
        base_timeout: Base timeout for operation (will be doubled each attempt). If None, timeout not modified.
        validation_func: Optional function to validate the result (returns True if valid)

    Returns:
        Result from operation_func if successful
    """
    for attempt in range(max_retries):
        try:
            # Calculer le timeout progressif pour cette tentative (+1s par tentative)
            current_timeout = None
            if base_timeout is not None:
                current_timeout = base_timeout + (1.0 * attempt)
                if attempt > 0:
                    logging.info(f"{operation_name} attempt {attempt + 1} using increased timeout: {current_timeout}s")

            # Exécuter l'opération avec timeout progressif si supporté
            result = operation_func(current_timeout) if base_timeout is not None else operation_func()

            # Si aucune validation spécifique, vérifier que le résultat existe et n'est pas vide
            if validation_func is None:
                if result and len(result) > 0:
                    # Vérifier qu'il n'y a pas d'erreur Parse error ou autre
                    if isinstance(result, list) and len(result) > 0:
                        first_result = result[0]
                        if 'error' in first_result:
                            error_code = first_result['error'].get('code', 0)
                            error_msg = first_result['error'].get('message', 'Unknown error')
                            # Parse error (-32700) ou autres erreurs critiques : retry
                            if error_code == -32700 or error_code < 0:
                                logging.warning(f"{operation_name} attempt {attempt + 1} failed with error {error_code}: {error_msg}")
                                if attempt < max_retries - 1:
                                    delay = base_delay * (2 ** attempt)
                                    logging.warning(f"Retrying {operation_name} in {delay}s...")
                                    time.sleep(delay)
                                    continue
                        elif 'result' in first_result:
                            # Succès
                            return result
                    return result
            else:
                # Utiliser la fonction de validation fournie
                if validation_func(result):
                    return result

            # Échec de validation : retry
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logging.warning(f"{operation_name} attempt {attempt + 1} failed validation, retrying in {delay}s...")
                time.sleep(delay)

        except Exception as e:
            logging.error(f"{operation_name} attempt {attempt + 1} raised exception: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logging.warning(f"Retrying {operation_name} in {delay}s...")
                time.sleep(delay)
            else:
                # Dernière tentative : laisser l'exception remonter
                raise

    # Si toutes les tentatives échouent, retourner le dernier résultat
    return result

def get_single_value(args: argparse.Namespace, field_name: str, source: str = "both") -> Any:
    """Helper function to get a single value from API response.

    Args:
        args: Command line arguments
        field_name: Name of the field to extract
        source: Which API to call - "es" for ES.GetMode, "bat" for Bat.GetStatus, "both" for all-status
    """
    local_bind = None
    if args.bind:
        host, port_str = args.bind.rsplit(":", 1)
        local_bind = (host, int(port_str))

    max_retries = getattr(args, 'command_retries', 3)

    # Fonction pour récupérer les données avec timeout dynamique
    def fetch_data(dynamic_timeout=None):
        # Utiliser le timeout dynamique si fourni, sinon utiliser args.timeout
        current_timeout = dynamic_timeout if dynamic_timeout is not None else args.timeout

        # Determine which API call(s) to make
        if source == "es":
            payload = {"id": 1, "method": "ES.GetMode", "params": {"id": 0}}
            return send_and_receive(args.ip, args.port, payload,
                                   timeout=current_timeout, retries=args.retries,
                                   local_bind=local_bind)
        elif source == "bat":
            payload = {"id": 1, "method": "Bat.GetStatus", "params": {"id": 0}}
            return send_and_receive(args.ip, args.port, payload,
                                   timeout=current_timeout, retries=args.retries,
                                   local_bind=local_bind)
        else:  # both
            calls = [
                {"id": 1, "method": "ES.GetMode", "params": {"id": 0}},
                {"id": 2, "method": "Bat.GetStatus", "params": {"id": 0}},
            ]
            results = []
            for call_payload in calls:
                call_results = send_and_receive(args.ip, args.port, call_payload,
                                               timeout=current_timeout, retries=args.retries,
                                               local_bind=local_bind)
                results.extend(call_results)
            return results

    # Fonction de validation : vérifier que le champ existe
    def validate_result(results):
        if not results or len(results) == 0:
            return False
        for res in results:
            if 'result' in res and field_name in res['result']:
                return True
        return False

    # Utiliser le système de retry intelligent avec timeout progressif
    results = execute_with_retry(
        operation_func=fetch_data,
        operation_name=f"get-{field_name}",
        max_retries=max_retries,
        base_delay=1.0,
        base_timeout=args.timeout,
        validation_func=validate_result
    )

    # Extract the field value
    for res in results:
        if 'result' in res and field_name in res['result']:
            value = res['result'][field_name]
            # Special conversion for bat_temp (convert to Celsius)
            if field_name == "bat_temp":
                return round(value / 10.0, 1)
            # Convert booleans to 1/0 for easier Jeedom integration
            elif isinstance(value, bool):
                return 1 if value else 0
            return value

    # Field not found même après retry
    print(json.dumps({"error": f"Field '{field_name}' not found in API response after {max_retries} attempts"}))
    sys.exit(1)

def execute_command(args: argparse.Namespace) -> List[Any]:
    local_bind = None
    if args.bind:
        host, port_str = args.bind.rsplit(":", 1)
        local_bind = (host, int(port_str))

    max_retries = getattr(args, 'command_retries', 3)

    # Logique pour la commande par défaut: all-status (le plus pertinent pour Jeedom)
    if args.cmd == "all-status":
        def fetch_all_status(dynamic_timeout=None):
            current_timeout = dynamic_timeout if dynamic_timeout is not None else args.timeout
            calls = [
                # Méthodes confirmées pour VenusE 3.0
                {"id": 1, "method": "ES.GetMode", "params": {"id": 0}},
                {"id": 2, "method": "Bat.GetStatus", "params": {"id": 0}},
            ]

            all_results = []
            for payload in calls:
                results = send_and_receive(args.ip, args.port, payload,
                                         timeout=current_timeout, retries=args.retries,
                                         local_bind=local_bind)
                # Ajouter tous les résultats (un par appel)
                all_results.extend(results)

            return all_results

        # Utiliser le retry intelligent avec timeout progressif
        return execute_with_retry(
            operation_func=fetch_all_status,
            operation_name="all-status",
            max_retries=max_retries,
            base_delay=1.0,
            base_timeout=args.timeout
        )

    # Pour les commandes simples d'état (GET) - Pour VenusE 3.0
    if args.cmd == "es-mode":
        def fetch_es_mode(dynamic_timeout=None):
            current_timeout = dynamic_timeout if dynamic_timeout is not None else args.timeout
            payload = {"id": 1, "method": "ES.GetMode", "params": {"id": args.id}}
            return send_and_receive(args.ip, args.port, payload,
                                   timeout=current_timeout, retries=args.retries,
                                   local_bind=local_bind)

        return execute_with_retry(
            operation_func=fetch_es_mode,
            operation_name="es-mode",
            max_retries=max_retries,
            base_delay=1.0,
            base_timeout=args.timeout
        )

    elif args.cmd == "bat-status":
        def fetch_bat_status(dynamic_timeout=None):
            current_timeout = dynamic_timeout if dynamic_timeout is not None else args.timeout
            payload = {"id": 1, "method": "Bat.GetStatus", "params": {"id": args.id}}
            return send_and_receive(args.ip, args.port, payload,
                                   timeout=current_timeout, retries=args.retries,
                                   local_bind=local_bind)

        return execute_with_retry(
            operation_func=fetch_bat_status,
            operation_name="bat-status",
            max_retries=max_retries,
            base_delay=1.0,
            base_timeout=args.timeout
        )

    # Commandes GET individuelles pour Jeedom (retourne une valeur unique)
    elif args.cmd == "get-mode":
        return get_single_value(args, "mode", source="es")
    elif args.cmd == "get-soc":
        return get_single_value(args, "soc", source="bat")
    elif args.cmd == "get-bat-soc":
        return get_single_value(args, "bat_soc", source="es")
    elif args.cmd == "get-bat-temp":
        return get_single_value(args, "bat_temp", source="bat")
    elif args.cmd == "get-bat-capacity":
        return get_single_value(args, "bat_capacity", source="bat")
    elif args.cmd == "get-rated-capacity":
        return get_single_value(args, "rated_capacity", source="bat")
    elif args.cmd == "get-charge-flag":
        return get_single_value(args, "charg_flag", source="bat")
    elif args.cmd == "get-discharge-flag":
        return get_single_value(args, "dischrg_flag", source="bat")
    elif args.cmd == "get-ongrid-power":
        return get_single_value(args, "ongrid_power", source="es")
    elif args.cmd == "get-offgrid-power":
        return get_single_value(args, "offgrid_power", source="es")
    elif args.cmd == "get-total-power":
        return get_single_value(args, "total_power", source="es")
    elif args.cmd == "get-a-power":
        return get_single_value(args, "a_power", source="es")
    elif args.cmd == "get-b-power":
        return get_single_value(args, "b_power", source="es")
    elif args.cmd == "get-c-power":
        return get_single_value(args, "c_power", source="es")
    elif args.cmd == "get-ct-state":
        return get_single_value(args, "ct_state", source="es")

    # Pour les commandes d'action (SET) - Pour VenusE 3.0
    elif args.cmd == "set-es-mode":
        # Ce cas ne renvoie qu'une réponse de succès
        config_params = {}
        if args.mode == "Auto":
            config_params["auto_cfg"] = {"enable": 1}
        elif args.mode == "AI":
            config_params["ai_cfg"] = {"enable": 1}
        elif args.mode == "Manual":
            config_params["manual_cfg"] = {
                "time_num": args.time_num,
                "start_time": args.start_time,
                "end_time": args.end_time,
                "week_set": args.week_set,
                "power": args.power,
                "enable": args.enable
            }
        elif args.mode == "Passive":
            config_params["passive_cfg"] = {
                "power": args.power,
                "cd_time": args.cd_time
            }

        payload = {
            "id": 1,
            "method": "ES.SetMode",
            "params": {
                "id": args.id,
                "config": {
                    "mode": args.mode,
                    **config_params
                }
            }
        }

        # Système de retry avec tempo progressive pour fiabiliser la commande
        max_command_retries = getattr(args, 'command_retries', 3)  # 3 tentatives par défaut
        base_delay = 2.0  # Délai de base en secondes

        for attempt in range(max_command_retries):
            results = send_and_receive(args.ip, args.port, payload,
                                       timeout=args.timeout, retries=args.retries,
                                       local_bind=local_bind)

            # Vérifier si la commande a réussi
            if results and len(results) > 0:
                result = results[0]
                if 'result' in result and 'set_result' in result['result']:
                    if result['result']['set_result'] is True:
                        # Succès confirmé
                        return results

            # Échec : attendre avant de réessayer (sauf à la dernière tentative)
            if attempt < max_command_retries - 1:
                # Tempo progressive : 2s, 4s, 8s...
                delay = base_delay * (2 ** attempt)
                logging.warning(f"set-es-mode attempt {attempt + 1} failed, retrying in {delay}s...")
                time.sleep(delay)

        # Si toutes les tentatives échouent, retourner le dernier résultat
        return results
    
    # Si la commande n'est pas supportée dans cette version simplifiée
    else:
        print(json.dumps({"error": "Command not supported in Jeedom connector."}))
        sys.exit(1)


def cli():
    p = argparse.ArgumentParser(description="UDP JSON client for Marstek V3 battery - Jeedom Connector")
    p.add_argument("--ip", default=DEFAULT_IP, help=f"Target IP (default: {DEFAULT_IP})")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Target UDP port (default: {DEFAULT_PORT})")
    p.add_argument("--timeout", type=float, default=2.0, help="Receive timeout (default: 2.0)")
    p.add_argument("--retries", type=int, default=2, help="Number of retries for network operations (default: 2)")
    p.add_argument("--command-retries", type=int, default=3, dest="command_retries", help="Number of command retry attempts for set-es-mode with progressive delay (default: 3)")
    p.add_argument("--bind", default=None, help="Bind to local ip:port (e.g. 0.0.0.0:30000)")

    sub = p.add_subparsers(dest="cmd", required=False)

    # Commandes de lecture (GET) - Pour VenusE 3.0
    sub.add_parser("all-status", help="Run all status API calls in sequence (Recommandé pour Jeedom)")

    sp_es_mode = sub.add_parser("es-mode", help="Send ES.GetMode request (mode, powers, SOC)")
    sp_es_mode.add_argument("--id", type=int, default=0, help="Device id (default: 0)")

    sp_bat = sub.add_parser("bat-status", help="Send Bat.GetStatus request (battery info)")
    sp_bat.add_argument("--id", type=int, default=0, help="Device id (default: 0)")

    # Commandes GET individuelles (retourne une valeur unique pour Jeedom)
    sub.add_parser("get-mode", help="Get current mode (Auto/AI/Manual/Passive)")
    sub.add_parser("get-soc", help="Get battery State of Charge in %% (from Bat.GetStatus)")
    sub.add_parser("get-bat-soc", help="Get battery SOC in %% (from ES.GetMode)")
    sub.add_parser("get-bat-temp", help="Get battery temperature in °C")
    sub.add_parser("get-bat-capacity", help="Get current battery capacity in Wh")
    sub.add_parser("get-rated-capacity", help="Get rated battery capacity in Wh")
    sub.add_parser("get-charge-flag", help="Get charge flag (1=charging, 0=not charging)")
    sub.add_parser("get-discharge-flag", help="Get discharge flag (1=discharging, 0=not discharging)")
    sub.add_parser("get-ongrid-power", help="Get on-grid power in W")
    sub.add_parser("get-offgrid-power", help="Get off-grid power in W")
    sub.add_parser("get-total-power", help="Get total power in W")
    sub.add_parser("get-a-power", help="Get phase A power in W")
    sub.add_parser("get-b-power", help="Get phase B power in W")
    sub.add_parser("get-c-power", help="Get phase C power in W")
    sub.add_parser("get-ct-state", help="Get CT (Current Transformer) state")

    # Commande set-es-mode pour l'action (SET)
    sp_set_mode = sub.add_parser(
        "set-es-mode",
        help="Send ES.SetMode request (WRITE mode)",
        epilog="""
Exemples d'utilisation:
  Mode Auto (gestion automatique):
    %(prog)s set-es-mode Auto

  Mode AI (intelligence artificielle):
    %(prog)s set-es-mode AI

  Mode Manual (plage horaire):
    %(prog)s set-es-mode Manual --power -1000 --start-time "08:00" --end-time "18:00" --week-set 127
    %(prog)s set-es-mode Manual --power 500 --start-time "22:00" --end-time "06:00" --week-set 31
    (⚠️ ATTENTION: power < 0: CHARGE, power > 0: DÉCHARGE, week-set: 127=tous les jours, 31=lun-ven)

  Mode Passive (mode bypass/passif - batterie inactive):
    %(prog)s set-es-mode Passive
    (place la batterie en mode passif/bypass, sans charge ni décharge active)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sp_set_mode.add_argument("--id", type=int, default=0, help="Device id (default: 0)")
    sp_set_mode.add_argument(
        "mode",
        type=str,
        choices=["Auto", "AI", "Manual", "Passive"],
        help="Mode de fonctionnement à définir (Auto, AI, Manual, Passive)"
    )
    # Arguments pour le mode Manual/Time Control
    sp_set_mode.add_argument("--time-num", type=int, default=1, help="Time period serial number (1-9)")
    sp_set_mode.add_argument("--start-time", type=str, default="00:00", help="Start time (hh:mm). Required for Manual mode.")
    sp_set_mode.add_argument("--end-time", type=str, default="23:59", help="End time (hh:mm). Required for Manual mode.")
    sp_set_mode.add_argument("--week-set", type=int, default=127, help="Weekly setting: 1=Mon, 2=Tue, 4=Wed, 8=Thu, 16=Fri, 32=Sat, 64=Sun, 127=All Week")
    sp_set_mode.add_argument("--power", type=int, default=100, help="Setting power in Watts. ⚠️ ATTENTION: NEGATIVE=charge, POSITIVE=discharge. Required for Manual mode. For Passive mode, parameter exists in API but actual function unclear.")
    sp_set_mode.add_argument("--enable", type=int, default=1, choices=[0, 1], help="ON: 1; OFF: 0. Required for Manual mode.")
    sp_set_mode.add_argument("--cd-time", type=int, default=300, help="Duration in seconds. For Passive mode, parameter exists in API but actual function unclear.")


    args = p.parse_args()

    # Si aucune commande n'est spécifiée, afficher l'aide
    if args.cmd is None:
        p.print_help()
        sys.exit(0)

    try:
        results = execute_command(args)

        # Commandes GET individuelles - retourne une valeur unique
        if args.cmd and args.cmd.startswith("get-"):
            # results contient directement la valeur (pas une liste)
            print(results)

        # Le connecteur Jeedom renvoie toujours une liste de résultats.
        # Pour le monitoring, nous affichons le JSON combiné pour une seule commande.
        elif args.cmd == "all-status" or args.cmd == "es-mode" or args.cmd == "bat-status":
            # Jeedom aura besoin des données pour les commandes info
            # On cherche l'objet result ou on combine tous les résultats
            final_output = {}
            for res in results:
                if 'result' in res:
                    final_output.update(res['result'])
                elif 'error' in res:
                    # Afficher l'erreur JSON pour le débug si une erreur survient
                    print(json.dumps(res, indent=2, ensure_ascii=False))
                    sys.exit(1)

            # Jeedom utilise le JSON comme source de données
            print(json.dumps(final_output, indent=2, ensure_ascii=False))

        elif args.cmd == "set-es-mode":
            # Pour les commandes d'action, le résultat est la confirmation.
            # On affiche juste la réponse pour confirmer l'action.
            if results and 'result' in results[0]:
                print(json.dumps({"success": True, "result": results[0]['result']}))
            else:
                # Si erreur, afficher la réponse complète de l'appareil
                print(json.dumps(results[0], indent=2, ensure_ascii=False))
                sys.exit(1)
                
    except Exception as e:
        print(json.dumps({"error": f"Internal Script Error: {e}"}, indent=2, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    try:
        cli()
    except SystemExit:
        # argparse peut générer un SystemExit, on le laisse passer
        pass
    except Exception as e:
        # Toutes autres erreurs non gérées
        print(json.dumps({"error": f"Unexpected execution error: {e}"}))
        sys.exit(1)