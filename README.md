# Client UDP Marstek pour Jeedom

Script Python pour communiquer avec une batterie de stockage d'énergie Marstek VenusE 3.0 via UDP.

## Prérequis

- Python 3.7 ou supérieur
- Batterie Marstek VenusE 3.0 accessible sur le réseau local

## Installation

```bash
# Aucune dépendance externe requise - utilise uniquement la bibliothèque standard Python
```

## Configuration

Par défaut, le script est configuré pour :
- **IP** : `192.168.0.182`
- **Port** : `30000`

Ces paramètres peuvent être modifiés via les arguments de ligne de commande.

## Utilisation

### Commandes disponibles

#### 1. Récupérer tous les statuts (recommandé pour Jeedom)

```bash
python marstek_udp_client_all_v3.py all-status
```

**Sortie JSON combinée** incluant :
- Mode de fonctionnement (Auto/AI/Manual/Passive)
- Puissances (ongrid, offgrid, par phase)
- État de charge de la batterie (SOC)
- Température de la batterie
- Capacité de la batterie
- Flags de charge/décharge

#### 2. Récupérer uniquement le mode et les puissances

```bash
python marstek_udp_client_all_v3.py es-mode
```

**Données retournées** :
- `mode` : Mode actuel (Auto, AI, Manual, Passive)
- `ongrid_power` : Puissance réseau (W)
- `offgrid_power` : Puissance hors-réseau (W)
- `bat_soc` : État de charge batterie (%)
- `ct_state` : État du transformateur de courant
- `a_power`, `b_power`, `c_power` : Puissance par phase (W)
- `total_power` : Puissance totale (W)

#### 3. Récupérer uniquement les informations batterie

```bash
python marstek_udp_client_all_v3.py bat-status
```

**Données retournées** :
- `soc` : État de charge (%)
- `charg_flag` : Indicateur de charge (true/false)
- `dischrg_flag` : Indicateur de décharge (true/false)
- `bat_temp` : Température batterie (0.1°C)
- `bat_capacity` : Capacité actuelle (Wh)
- `rated_capacity` : Capacité nominale (Wh)

#### 4. Commandes GET individuelles (valeur unique - idéal pour Jeedom)

Ces commandes retournent **une seule valeur** (pas de JSON), parfait pour une intégration directe dans Jeedom sans parsing.

##### Informations générales
```bash
# Mode de fonctionnement actuel
python marstek_udp_client_all_v3.py get-mode
# Retourne: Auto, AI, Manual ou Passive

# État de charge (SOC) de la batterie
python marstek_udp_client_all_v3.py get-soc
# Retourne: 98 (en %)

# État de charge depuis ES.GetMode
python marstek_udp_client_all_v3.py get-bat-soc
# Retourne: 98 (en %)
```

##### Informations batterie
```bash
# Température de la batterie (conversion automatique en °C)
python marstek_udp_client_all_v3.py get-bat-temp
# Retourne: 31.6 (en °C)

# Capacité actuelle de la batterie
python marstek_udp_client_all_v3.py get-bat-capacity
# Retourne: 512 (en Wh)

# Capacité nominale de la batterie
python marstek_udp_client_all_v3.py get-rated-capacity
# Retourne: 5120 (en Wh)

# Flag de charge (1=en charge, 0=pas en charge)
python marstek_udp_client_all_v3.py get-charge-flag
# Retourne: 1 ou 0

# Flag de décharge (1=en décharge, 0=pas en décharge)
python marstek_udp_client_all_v3.py get-discharge-flag
# Retourne: 1 ou 0
```

##### Puissances
```bash
# Puissance totale
python marstek_udp_client_all_v3.py get-total-power
# Retourne: 0 (en W)

# Puissance réseau (on-grid)
python marstek_udp_client_all_v3.py get-ongrid-power
# Retourne: 0 (en W)

# Puissance hors-réseau (off-grid)
python marstek_udp_client_all_v3.py get-offgrid-power
# Retourne: 0 (en W)

# Puissance phase A
python marstek_udp_client_all_v3.py get-a-power
# Retourne: 0 (en W)

# Puissance phase B
python marstek_udp_client_all_v3.py get-b-power
# Retourne: 0 (en W)

# Puissance phase C
python marstek_udp_client_all_v3.py get-c-power
# Retourne: 0 (en W)

# État du transformateur de courant
python marstek_udp_client_all_v3.py get-ct-state
# Retourne: 0
```

#### 5. Changer le mode de fonctionnement (set-es-mode)

##### Mode Auto (gestion automatique)
Le système gère automatiquement la charge/décharge selon la production solaire et la consommation.

```bash
python marstek_udp_client_all_v3.py set-es-mode Auto
```

##### Mode AI (intelligence artificielle)
Le système utilise l'IA pour optimiser la gestion énergétique.

```bash
python marstek_udp_client_all_v3.py set-es-mode AI
```

##### Mode Manual (contrôle par plage horaire)
Permet de définir des plages horaires avec charge/décharge programmée.

**Paramètres :**
- `--power` : Puissance en Watts ⚠️ **ATTENTION : négatif=charge, positif=décharge**
- `--start-time` : Heure de début (format HH:MM)
- `--end-time` : Heure de fin (format HH:MM)
- `--week-set` : Jours de la semaine (binaire)
  - 1 = Lundi
  - 2 = Mardi
  - 4 = Mercredi
  - 8 = Jeudi
  - 16 = Vendredi
  - 32 = Samedi
  - 64 = Dimanche
  - 127 = Tous les jours (1+2+4+8+16+32+64)
  - 31 = Lundi à Vendredi (1+2+4+8+16)
  - 96 = Week-end (32+64)
- `--enable` : Activer la plage (1=ON, 0=OFF)
- `--time-num` : Numéro de la plage horaire (1-9)

**Exemples :**

```bash
# Charger à 1000W de 8h à 18h tous les jours
python marstek_udp_client_all_v3.py set-es-mode Manual --power -1000 --start-time "08:00" --end-time "18:00" --week-set 127

# Décharger à 500W de 22h à 6h du lundi au vendredi
python marstek_udp_client_all_v3.py set-es-mode Manual --power 500 --start-time "22:00" --end-time "06:00" --week-set 31

# Charger à 800W le week-end de 10h à 16h
python marstek_udp_client_all_v3.py set-es-mode Manual --power -800 --start-time "10:00" --end-time "16:00" --week-set 96

# Désactiver une plage horaire
python marstek_udp_client_all_v3.py set-es-mode Manual --enable 0 --time-num 1
```

##### Mode Passive (mode bypass/passif)
Place la batterie en mode passif/bypass (équivalent au "Bypass Mode" dans l'application Marstek).
Dans ce mode, la batterie reste inactive sans charge ni décharge active.

**Note :** Les paramètres `--power` et `--cd-time` sont requis par l'API mais leur fonction exacte en mode Passive n'est pas documentée clairement. Ce mode semble principalement servir à désactiver temporairement la batterie.

**Paramètres :**
- `--power` : Paramètre requis par l'API (valeur par défaut: 100W)
- `--cd-time` : Durée en secondes (valeur par défaut: 300s)

**Exemple :**

```bash
# Activer le mode passif/bypass
python marstek_udp_client_all_v3.py set-es-mode Passive
```

### Options globales

```bash
--ip IP                    # Adresse IP de la batterie (défaut: 192.168.0.182)
--port PORT                # Port UDP (défaut: 30000)
--timeout TIMEOUT          # Timeout de réception en secondes (défaut: 2.0)
--retries RETRIES          # Nombre de tentatives réseau (défaut: 2)
--command-retries RETRIES  # Nombre de tentatives pour set-es-mode avec délai progressif (défaut: 3)
--bind BIND                # Bind local ip:port (ex: 0.0.0.0:30000)
--verbose                  # Affiche les messages de retry (désactivé par défaut pour Jeedom)
```

**Notes importantes :**
- **--command-retries :** Pour fiabiliser l'envoi des commandes `set-es-mode`, le script réessaie automatiquement jusqu'à 3 fois avec des délais progressifs (2s, 4s, 8s) en cas d'échec. Vous pouvez ajuster ce nombre avec `--command-retries`.
- **--verbose :** Par défaut, les messages de retry sont **masqués** pour ne pas polluer la sortie JSON dans Jeedom. Activez cette option uniquement pour le débogage ou les tests manuels.

### Exemples d'utilisation avancés

#### Configuration réseau

```bash
# Avec une IP différente
python marstek_udp_client_all_v3.py --ip 192.168.1.100 all-status

# Avec timeout personnalisé
python marstek_udp_client_all_v3.py --timeout 3.0 all-status

# Avec bind local personnalisé
python marstek_udp_client_all_v3.py --bind 0.0.0.0:30001 all-status

# Augmenter le nombre de tentatives pour set-es-mode (en cas de réseau instable)
python marstek_udp_client_all_v3.py --command-retries 5 set-es-mode Manual --power -2000 --start-time "22:00" --end-time "06:00" --week-set 127

# Activer le mode verbose pour le débogage (affiche les retry sur stderr)
python marstek_udp_client_all_v3.py --verbose get-mode
python marstek_udp_client_all_v3.py --verbose --command-retries 5 set-es-mode Auto
```

**Note :** Le mode `--verbose` affiche les messages de retry sur **stderr** (erreur standard), ce qui permet de les distinguer de la sortie JSON sur **stdout**. Ceci est utile pour le débogage sans impacter Jeedom.

#### Scénarios d'utilisation du mode Manual

**Scénario 1 : Charger la batterie pendant les heures creuses (tarif jour/nuit)**
```bash
# Charger à 2000W de 22h à 6h tous les jours (valeur NÉGATIVE pour la charge)
python marstek_udp_client_all_v3.py set-es-mode Manual --power -2000 --start-time "22:00" --end-time "06:00" --week-set 127
```

**Scénario 2 : Décharger pendant les heures pleines**
```bash
# Décharger à 1500W de 17h à 21h en semaine (valeur POSITIVE pour la décharge)
python marstek_udp_client_all_v3.py set-es-mode Manual --power 1500 --start-time "17:00" --end-time "21:00" --week-set 31
```

**Scénario 3 : Optimisation week-end**
```bash
# Charger à 1000W le samedi et dimanche de 12h à 16h (surplus solaire)
python marstek_udp_client_all_v3.py set-es-mode Manual --power -1000 --start-time "12:00" --end-time "16:00" --week-set 96
```

**Scénario 4 : Multiples plages horaires**
```bash
# Plage 1 : Charge heures creuses (NÉGATIF = charge)
python marstek_udp_client_all_v3.py set-es-mode Manual --time-num 1 --power -2000 --start-time "22:00" --end-time "06:00" --week-set 127

# Plage 2 : Décharge heures pleines (POSITIF = décharge)
python marstek_udp_client_all_v3.py set-es-mode Manual --time-num 2 --power 1500 --start-time "17:00" --end-time "21:00" --week-set 31
```

#### Scénarios d'utilisation du mode Passive

**Note :** Le mode Passive semble correspondre au mode "Bypass" de l'application Marstek. Il place la batterie en mode passif sans charge ni décharge active. Les scénarios d'utilisation typiques incluent :

**Scénario 1 : Désactivation temporaire de la batterie**
```bash
# Mettre la batterie en mode passif/bypass
python marstek_udp_client_all_v3.py set-es-mode Passive
```

**Scénario 2 : Maintenance ou diagnostic**
```bash
# Passer en mode passif avant une intervention technique
python marstek_udp_client_all_v3.py set-es-mode Passive
```

## Intégration Jeedom

### Méthode 1 : Commandes GET individuelles (RECOMMANDÉE)

Cette méthode est **la plus simple** car elle retourne directement une valeur unique sans nécessiter de parsing JSON.

#### Configuration dans Jeedom

1. **Plugins → Programmation → Script**
2. **Ajouter un équipement** : "Batterie Marstek"
3. **Créer des commandes Info** de type "Numérique" ou "Autre" :

**Exemple de configuration pour le SOC :**
- **Nom** : `SOC Batterie`
- **Type** : Info / Numérique
- **Sous-type** : Numérique
- **Unité** : `%`
- **Requête Script** :
  ```bash
  python3 /chemin/vers/marstek_udp_client_all_v3.py get-soc
  ```

**Liste complète des commandes Info recommandées :**

| Nom de la commande | Requête Script | Unité | Type |
|-------------------|----------------|-------|------|
| SOC Batterie | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-soc` | % | Numérique |
| Mode | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-mode` | - | Autre |
| Température Batterie | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-bat-temp` | °C | Numérique |
| Puissance Totale | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-total-power` | W | Numérique |
| Capacité Actuelle | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-bat-capacity` | Wh | Numérique |
| Capacité Nominale | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-rated-capacity` | Wh | Numérique |
| En Charge | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-charge-flag` | - | Binaire |
| En Décharge | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-discharge-flag` | - | Binaire |
| Puissance Réseau | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-ongrid-power` | W | Numérique |
| Puissance Phase A | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-a-power` | W | Numérique |
| Puissance Phase B | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-b-power` | W | Numérique |
| Puissance Phase C | `python3 /chemin/vers/marstek_udp_client_all_v3.py get-c-power` | W | Numérique |

#### Commandes Action

**Passer en mode Auto :**
- **Nom** : `Mode Auto`
- **Type** : Action / Défaut
- **Requête** :
  ```bash
  python3 /chemin/vers/marstek_udp_client_all_v3.py set-es-mode Auto
  ```

**Passer en mode AI :**
- **Nom** : `Mode AI`
- **Type** : Action / Défaut
- **Requête** :
  ```bash
  python3 /chemin/vers/marstek_udp_client_all_v3.py set-es-mode AI
  ```

**Charger en heures creuses (exemple) :**
- **Nom** : `Charge Heures Creuses`
- **Type** : Action / Défaut
- **Requête** :
  ```bash
  python3 /chemin/vers/marstek_udp_client_all_v3.py set-es-mode Manual --power -2000 --start-time "22:00" --end-time "06:00" --week-set 127
  ```

#### Automatisation avec Cron

Pour mettre à jour automatiquement les valeurs toutes les 5 minutes :

1. Créez un **scénario** ou utilisez le **plugin Cron**
2. Programmation : `*/5 * * * *` (toutes les 5 minutes)
3. Actions : Rafraîchir toutes vos commandes Info

### Scénario Jeedom d'Optimisation Tarifaire (EDF Tempo)

Un **scénario avancé** de gestion énergétique est disponible pour optimiser automatiquement la charge de la batterie en fonction :
- **Tarif EDF Tempo** (Jours Rouges/Blancs/Bleus)
- **Prévisions météorologiques** (production solaire attendue)
- **Heures Creuses** (déclenchement de la charge entre 01h00 et 05h45)

#### Principe de fonctionnement

Le scénario utilise un algorithme de **"Smart Charging"** qui :
1. **Analyse** la couleur Tempo du jour suivant et les prévisions météo
2. **Détermine** un SOC cible optimal (0% à 100%) pour la fin des heures creuses
3. **Calcule dynamiquement** la puissance de charge minimale nécessaire toutes les 15 minutes
4. **Optimise** le rendement en évitant les charges à faible puissance
5. **Repasse automatiquement** en mode Autoconsommation à 5h45

**Exemples de stratégie :**
- **Jour Rouge** : Charge à 100% (éviter les tarifs élevés)
- **Jour Blanc + Nuageux** : Charge à 100% (faible production solaire prévue)
- **Jour Blanc + Ensoleillé** : Charge à 30% (le solaire complétera)
- **Jour Bleu** : Charge à 0% (tarif faible, priorité au solaire)

📄 **Documentation complète** : Voir [JEEDOM Scenario.md](JEEDOM%20Scenario.md) pour l'algorithme détaillé et l'implémentation pas à pas.

📸 **Captures d'écran** : Consultez le dossier `Jeedom captures/` pour voir la configuration complète dans l'interface Jeedom.

### Méthode 2 : Parsing JSON (alternative)

Si vous préférez récupérer toutes les données en une seule fois et parser le JSON :

```bash
python3 /chemin/vers/marstek_udp_client_all_v3.py all-status
```

**Exemples de parsing dans Jeedom :**
- **État de charge (SOC)** : Extraire `soc` du JSON
- **Mode** : Extraire `mode` du JSON
- **Puissance totale** : Extraire `total_power` du JSON
- **Température batterie** : Extraire `bat_temp` du JSON et diviser par 10

### Exemple de Widget Jeedom

Pour créer un affichage visuel :

1. Dans le **Dashboard**, ajoutez vos commandes
2. Personnalisez avec des icônes :
   - 🔋 pour le SOC
   - ⚡ pour la puissance
   - 🌡️ pour la température
   - ⚙️ pour le mode
3. Créez des **conditions d'affichage** :
   - SOC < 20% → Couleur rouge
   - SOC 20-50% → Couleur orange
   - SOC > 50% → Couleur verte

## Tableau récapitulatif des commandes

### Commandes GET (lecture)

| Commande | Retour | Unité | Description |
|----------|--------|-------|-------------|
| `all-status` | JSON | - | Retourne toutes les données combinées (ES + Bat) |
| `es-mode` | JSON | - | Retourne les données ES.GetMode |
| `bat-status` | JSON | - | Retourne les données Bat.GetStatus |
| `get-mode` | Texte | - | Mode actuel (Auto/AI/Manual/Passive) |
| `get-soc` | Nombre | % | État de charge batterie (Bat.GetStatus) |
| `get-bat-soc` | Nombre | % | État de charge batterie (ES.GetMode) |
| `get-bat-temp` | Nombre | °C | Température batterie (conversion auto) |
| `get-bat-capacity` | Nombre | Wh | Capacité actuelle batterie |
| `get-rated-capacity` | Nombre | Wh | Capacité nominale batterie |
| `get-charge-flag` | 0 ou 1 | - | 1 = en charge, 0 = pas en charge |
| `get-discharge-flag` | 0 ou 1 | - | 1 = en décharge, 0 = pas en décharge |
| `get-total-power` | Nombre | W | Puissance totale |
| `get-ongrid-power` | Nombre | W | Puissance réseau (on-grid) |
| `get-offgrid-power` | Nombre | W | Puissance hors-réseau (off-grid) |
| `get-a-power` | Nombre | W | Puissance phase A |
| `get-b-power` | Nombre | W | Puissance phase B |
| `get-c-power` | Nombre | W | Puissance phase C |
| `get-ct-state` | Nombre | - | État du transformateur de courant |

### Commandes SET (écriture)

| Commande | Paramètres | Description |
|----------|-----------|-------------|
| `set-es-mode Auto` | - | Passe en mode automatique |
| `set-es-mode AI` | - | Passe en mode Intelligence Artificielle |
| `set-es-mode Manual` | `--power`, `--start-time`, `--end-time`, `--week-set` | Passe en mode manuel avec plage horaire |
| `set-es-mode Passive` | `--power`, `--cd-time` | Passe en mode passif/bypass (batterie inactive) |

## Méthodes API supportées

Le script utilise les méthodes API suivantes compatibles avec VenusE 3.0 :

| Méthode | Description |
|---------|-------------|
| `ES.GetMode` | Récupère le mode de fonctionnement et les puissances |
| `Bat.GetStatus` | Récupère l'état de la batterie |
| `ES.SetMode` | Change le mode de fonctionnement (écriture) |

**Note** : Contrairement à la documentation officielle générique Marstek qui mentionne `Inverter.*`, `Battery.*`, `PV.*`, le modèle VenusE 3.0 utilise les anciennes méthodes `ES.*` et `Bat.*`.

## Fiabilité et Système de Retry Intelligent

**TOUTES les commandes** (GET et SET) disposent désormais d'un **système de retry automatique intelligent** pour garantir la fiabilité de la communication avec la batterie.

### Fonctionnement

Le système détecte automatiquement les erreurs et réessaie l'opération :

#### Erreurs détectées et gérées :
- **Parse error (code -32700)** : Erreur de décodage JSON
- **Réponse vide** : Aucune donnée reçue
- **Champ manquant** : Le champ demandé n'existe pas dans la réponse
- **Timeout réseau** : Pas de réponse dans le délai imparti

#### Mécanisme de retry :
1. **Détection automatique** : Le script détecte si la réponse est valide
2. **Délai progressif** : Si échec, retry avec délai croissant (1s, 2s, 4s, 8s...)
3. **Timeout progressif** : Le timeout réseau augmente à chaque tentative (+1s par retry : 2.0s, 3.0s, 4.0s, 5.0s...)
   - Permet d'attendre plus longtemps si la batterie est temporairement surchargée
   - Améliore significativement la fiabilité sur réseau instable
4. **Validation spécifique** :
   - **Commandes GET** : Vérifie que les données demandées sont présentes
   - **Commandes SET** : Vérifie que `"set_result": true`
5. **Maximum 3 tentatives** par défaut (configurable avec `--command-retries`)

### Exemples

```bash
# Utilisation normale - toutes les commandes utilisent le retry automatique
python marstek_udp_client_all_v3.py all-status
python marstek_udp_client_all_v3.py get-mode
python marstek_udp_client_all_v3.py set-es-mode Auto

# Réseau instable : augmenter à 5 tentatives
python marstek_udp_client_all_v3.py --command-retries 5 all-status
python marstek_udp_client_all_v3.py --command-retries 5 get-soc
python marstek_udp_client_all_v3.py --command-retries 5 set-es-mode Manual --power -2000 --start-time "22:00" --end-time "06:00" --week-set 127

# Batterie très sollicitée ou connexion lente : augmenter le timeout de base
python marstek_udp_client_all_v3.py --timeout 3.0 all-status
python marstek_udp_client_all_v3.py --timeout 3.0 --command-retries 5 get-soc

# Combiner timeout élevé + plus de tentatives pour fiabilité maximale
python marstek_udp_client_all_v3.py --timeout 3.0 --command-retries 5 set-es-mode Manual --power -2000 --start-time "22:00" --end-time "06:00" --week-set 127
```

### Temps maximum d'attente

Le système combine **délai progressif** (pause entre tentatives) et **timeout progressif** (temps d'attente de réponse).

**Pour les commandes GET (timeout par défaut: 2.0s) :**
- **Tentative 1** : délai 0s + timeout 2.0s = 2.0s
- **Tentative 2** : délai 1s + timeout 3.0s = 4.0s
- **Tentative 3** : délai 2s + timeout 4.0s = 6.0s
- **Total 3 tentatives** : ~12 secondes maximum

**Pour les commandes SET (timeout par défaut: 2.0s, délai de base: 2s) :**
- **Tentative 1** : délai 0s + timeout 2.0s = 2.0s
- **Tentative 2** : délai 2s + timeout 3.0s = 5.0s
- **Tentative 3** : délai 4s + timeout 4.0s = 8.0s
- **Total 3 tentatives** : ~15 secondes maximum

**Avec timeout personnalisé (ex: --timeout 5.0) :**
- Les timeouts deviennent : 5.0s, 6.0s, 7.0s, 8.0s... (+1s à chaque retry)
- Utile pour connexions très lentes ou batterie très sollicitée

### Exemples d'erreurs gérées automatiquement

**Parse error :**
```json
{
  "error": {
    "code": -32700,
    "message": "Parse error",
    "data": 403
  }
}
```
→ **Retry automatique**

**Champ manquant :**
```json
{"error": "Field 'mode' not found in API response"}
```
→ **Retry automatique**

Ces erreurs, fréquentes avec la batterie Marstek, sont maintenant gérées de manière transparente !

## Dépannage

### Erreur de connexion

Si vous obtenez une erreur de timeout :
- Vérifiez que l'adresse IP est correcte
- Vérifiez que le port 30000 n'est pas bloqué par un pare-feu
- Vérifiez que la batterie est allumée et accessible sur le réseau

### Port déjà utilisé

Si le port 30000 est déjà occupé :
- Attendez quelques secondes entre les commandes
- Ou utilisez `--bind 0.0.0.0:30001` pour un port différent

### Method not found

Si vous obtenez "Method not found" :
- Votre modèle de batterie peut utiliser une API différente
- Utilisez les scripts de test fournis (`test_methods2.py`) pour identifier les méthodes supportées

### Commandes qui échouent systématiquement

Si les commandes (GET ou SET) échouent même après retry automatique :

**Stratégie progressive de dépannage :**

1. **Augmentez le timeout de base** : `--timeout 3.0` ou `--timeout 5.0`
   - Grâce au **timeout progressif**, le script attendra 3s, 4s, 5s... ou 5s, 6s, 7s... (+1s à chaque retry)
   - Particulièrement utile si la batterie est lente à répondre ou très sollicitée

2. **Augmentez le nombre de tentatives** : `--command-retries 5` ou `--command-retries 7`
   - Plus de chances de succès avec des délais exponentiels

3. **Combinez les deux** pour fiabilité maximale :
   ```bash
   python marstek_udp_client_all_v3.py --timeout 3.0 --command-retries 5 all-status
   ```

4. **Vérifiez la connexion réseau** entre votre système et la batterie

5. **Vérifiez que la batterie n'est pas surchargée** par l'application mobile simultanément

6. **Vérifiez les logs** : Le script affiche des warnings lors des retries et des timeouts progressifs

## Version

**Version 3.0** - Adaptée pour Marstek VenusE 3.0

## Licence

Ce script est fourni tel quel pour usage personnel et éducatif.

## Crédits

Ce script est largement inspiré du travail de slanckma : https://gist.github.com/slanckma/b94a6d77b81104ae441b217a669e55d7