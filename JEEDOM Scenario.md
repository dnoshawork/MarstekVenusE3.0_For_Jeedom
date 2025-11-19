Markdown
**Algorithme de Gestion Énergétique Hybride**

**Système :** Solaire 6kWc + Batterie 5.2kWh + EDF Tempo + Prévisions Météo

**Objectif :** Maximisation des gains (Arbitrage HP/HC) et de l'autoconsommation en fonction de la **couleur du jour Tempo** et de l'ensoleillement prévu.

**1\. Vue d'ensemble de la Stratégie**

Le système repose sur une logique d'anticipation météorologique et tarifaire. L'objectif principal est de **sécuriser l'alimentation électrique** durant les jours chers (Rouges/Blancs) en utilisant les Heures Creuses (HC) nocturnes, tout en laissant la priorité au solaire durant les jours bon marché (Bleus).

**Paramètres Clés**

- **Batterie :** 5.2 kWh (Utilisable)
- **Chargeur :** Puissance variable de 100 W à 2500 W
- **Cible Temporelle :** Batterie chargée à la cible définie pour **05h45** (Fin des HC)
- **Période de Pilotage :** De 01h00 à 05h45 (toutes les 15 min)

**2\. Phase A : Planification Nocturne (Matrice de Décision)**

Cette phase détermine le **SOC Cible** (State of Charge) à atteindre au petit matin. Elle s'exécute en début de nuit (ex: 01h00).

| Couleur du Jour (Demain) | Prévision Météo | SOC Cible (Fin de nuit) | Justification |
| --- | --- | --- | --- |
| 🔴 ROUGE | _Indifférent_ | **100 %** | Priorité absolue : éviter le soutirage en HP Rouge (~75cts/kWh). |
| ⚪ BLANC | ☁️ Nuageux / Pluie | **100 %** | Faible production solaire prévue, on sécurise le stock en HC. |
| ⚪ BLANC | ⛅ Partiellement couvert | **60 %** | Stock tampon pour le matin, le solaire complétera l'après-midi. |
| ⚪ BLANC | ☀️ Ensoleillé | **30 %** | Juste le nécessaire pour le pic du matin (café/douche). |
| 🔵 BLEU | _Indifférent_ | **0 %** | Le coût réseau est faible. On laisse la batterie vide pour maximiser le stockage solaire gratuit le lendemain. |

**3\. Phase B : Algorithme de "Smart Charging" (Lissage)**

Plutôt que de charger à pleine puissance (2500W) immédiatement, l'algorithme calcule dynamiquement la puissance minimale nécessaire pour atteindre l'objectif à 05h45 précises.

**La Formule Mathématique**

Le calcul est effectué itérativement (ex: toutes les 15 min).

\$\$Puissance (W) = \\frac{\\text{Énergie Manquante (Wh)}}{\\text{Temps Restant (h)}}\$\$

Où :

- **Énergie Manquante** = (SOC_Cible - SOC_Actuel) \* 52 Wh (car 1% de 5200Wh = 52Wh)
- **Temps Restant** = 5.75 - Heure_Actuelle_Decimale (5.75 correspond à 05h45)

**Optimisation & Sécurités**

- **Plafond (Max) :** 2500 W (Limite physique du chargeur).
- **Arrondi :** Valeur entière stricte.
- **Gestion du Rendement (Seuil 500W) :**
  - Si la puissance calculée est **< 500 W** (rendement onduleur médiocre) :
    - Si on a le temps (> 1h) : **0 W** (On attend que le besoin augmente).
    - Si on est pressé (< 1h) : **500 W** (On force la charge min pour finir à temps).

**4\. Implémentation Technique (Scénario Jeedom)**

Cette section détaille l'intégralité du scénario, incluant la logique de décision initiale puis le calcul de charge.

**Déclencheur :** Programmé \*/15 1-5 \* \* \* (Toutes les 15 min entre 01h00 et 05h45) + Une fois à 05h45.

**Partie 0 : Vérification de l'heure (Retour Auto à 5h45)**

| Type | Condition | Action / Valeur |
| --- | --- | --- |
| SI  | #time# >= 0545 | _Fin de la période HC, retour en mode Auto_ |
| &nbsp; ALORS | [Commande Batterie] | set-es-mode Auto |
| &nbsp; ALORS | STOP | _Arrêt du scénario_ |

**Partie 1 : Définition de la Cible (Matrice de décision)**

_(Cette partie s'exécute uniquement si #time# < 0545)_

| Type | Condition | Action / Valeur |
| --- | --- | --- |
| SI  | #\[Tempo\]\[Demain\]# == "ROUGE" |     |
| &nbsp; ALORS |     | variable (Nom: SOC_Cible) Valeur: 100 |
| SINON |     |     |
| &nbsp; SI | #\[Tempo\]\[Demain\]# == "BLANC" |     |
| &nbsp;   ALORS |     |     |
| &nbsp;     SI | #\[Météo\]\[Condition\]# == "Nuageux/Pluie" |     |
| &nbsp;       ALORS |     | variable (Nom: SOC_Cible) Valeur: 100 |
| &nbsp;     SINON |     |     |
| &nbsp;       SI | #\[Météo\]\[Condition\]# == "Partiellement Couvert" |     |
| &nbsp;         ALORS |     | variable (Nom: SOC_Cible) Valeur: 60 |
| &nbsp;         SINON | _(C'est donc Ensoleillé)_ | variable (Nom: SOC_Cible) Valeur: 30 |
| &nbsp; SINON | _(C'est donc BLEU)_ | variable (Nom: SOC_Cible) Valeur: 0 |

**Partie 2 : Calcul et Pilotage (Smart Charging)**

_(À la suite du bloc précédent dans le même scénario)_

| Type | Condition / Détails | Action / Valeur |
| --- | --- | --- |
| ACTION | variable (Nom: Delta_SOC) | variable(SOC_Cible) - #\[Garage\]\[Batterie\]\[SOC\]# |
| SI  | variable(Delta_SOC) <= 0 | _La batterie est assez chargée_ |
| &nbsp; ALORS | \[Commande Batterie\] | Message : 0 |
| &nbsp; SINON |     | _On doit charger_ |
| &nbsp;   ACTION | variable (Nom: Temps_Restant) | 5.75 - (floor(#time#/100) + (#time#%100)/60) |
| &nbsp;   ACTION | variable (Nom: Puissance_Consigne) | round((variable(Delta_SOC) \* 52) / variable(Temps_Restant)) |
| &nbsp;   ACTION | variable (Nom: Puissance_Consigne) | min(2500, variable(Puissance_Consigne)) |
| &nbsp;   SI | variable(Puissance_Consigne) < 500 | _Optimisation Rendement_ |
| &nbsp;     ALORS |     |     |
| &nbsp;       SI | variable(Temps_Restant) > 1 | _On a le temps, on attend_ |
| &nbsp;         ALORS | variable (Nom: Puissance_Consigne) | 0   |
| &nbsp;         SINON | variable (Nom: Puissance_Consigne) | 500 (_Pressé : charge forcée_) |
| &nbsp;   ACTION | \[Commande Batterie\] | Message : variable(Puissance_Consigne) |

**5\. Gestion Diurne (Bonus)**

Une fois le jour levé (après 06h00), la logique s'inverse pour maximiser l'autoconsommation.

- **Surplus Solaire :**
  - Si Prod_Solaire > Conso_Maison → Charger Batterie.
  - Si Batterie 100% → Déclencher Chauffe-eau ou Injection réseau.
- **Sécurité Soirée (Jours Rouges Uniquement) :**
  - Si Heure > 17h00 et Jour = ROUGE et Météo != Ensoleillé :
  - **Règle :** Brider la décharge batterie si SOC < 30%.
  - **But :** Garder une réserve pour le pic de consommation de 19h00-20h00 (Cuisine/Lumière) quand le soleil est couché.