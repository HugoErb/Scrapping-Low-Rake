# Scraping des taux de retours de matchs avec alerte Discord

Le taux de retour dans les paris sportifs, également appelé taux de redistribution ou taux de paiement, est un pourcentage qui représente la proportion des mises qui est redistribuée aux parieurs sous forme de gains. Par exemple, si le taux de retour est de 90%, cela signifie que pour chaque euro misé, en moyenne 0,90€ sont redistribués aux parieurs, tandis que 0,05€ sont conservés par l'opérateur de paris. Le taux de retour est un indicateur important de la rentabilité des paris sportifs pour les parieurs. Plus le taux de retour est élevé, plus les chances de gagner des gains à long terme sont élevées.

Ce projet utilise Playwright pour scraper les cotes des matchs depuis un site de comparaison de cotes et envoie des alertes sur Discord lorsque les taux de retour dépassent un certain seuil ou augmentent significativement par rapport à une précédente alerte. Il est conçu pour fonctionner en continu, vérifiant périodiquement les cotes toutes les `CHECK_INTERVAL_MINUTES` minutes et envoyant des alertes si nécessaire.

## Fonctionnalités

- Scraping des cotes depuis un site de comparaison.
- Envoi d'alertes sur un canal Discord via un webhook.
- Les alertes sont déclenchées lorsqu'un match dépasse un seuil de retour minimum défini par l'utilisateur.
- Le bot renvoie une nouvelle alerte si le pourcentage de retour d'un match augmente d'au moins `MIN_RETURN_INCREASE` (par défaut 0.1%).
- Le script continue de fonctionner même en cas d'erreurs et vérifie les cotes à intervalles réguliers.
- Ajout automatique de l'horodatage au format français à chaque message (avec un décalage de 2 heures pour compenser l'heure du serveur).

## Prérequis

Avant de commencer, assurez-vous d'avoir installé les éléments suivants sur le serveur ou ce projet doit tourner en continu :

- Python 3.7 ou plus récent
- Playwright
- DiscordWebhook

## Installation

1. **Clonez ce dépôt :**

   ```bash
   git clone https://github.com/ton-dossier/scraping-cotes.git
   cd scraping-cotes
   ```
   
2. **Installez les dépendances requises :**

    ```bash
   pip install -r requirements.txt
   playwright install
    ```

3. **Configurer votre webhook Discord :**

    ```bash
   # constants.py
   DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/votre_webhook'
    ```

## Utilisation

Pour démarrer le bot de scraping, exécutez le fichier Python principal :

   ```bash
   python scrapper.py
   ```

Pour une utilisation sur VPS, avec nohup :

Lancer le script : 
```nohup python3 scrapper.py > output.log 2>&1```

Affiche tous les processus en cours d'exécution qui ont été démarrés avec nohup :
```ps aux | grep '[n]ohup'```

Terminer tous les processus en arrière-plan liés à nohup :
```pkill -f nohup```

Le bot va :

- Scraper les cotes de matchs à partir du site.
- Envoyer des alertes sur Discord si les conditions sont remplies.
- Continuer de vérifier toutes les CHECK_INTERVAL_MINUTES minutes.

## Personnalisation

Configuration des constantes
Les paramètres principaux peuvent être modifiés dans le fichier constants.py :

- RETURN_THRESHOLD : Le seuil de pourcentage de retour minimum pour qu'une alerte soit envoyée (par défaut 98.0).
- MAX_RETURN_THRESHOLD : Le pourcentage de retour maximum considéré pour une alerte (par défaut 105.0).
- MIN_RETURN_INCREASE : Le pourcentage d'augmentation requis pour renvoyer une alerte pour un match déjà signalé (par défaut 0.1%).
- CHECK_INTERVAL_MINUTES : Le nombre de minutes entre chaque vérification des cotes (par défaut 5 minutes).
- JS_LOAD_TIMEOUT : Le temps maximum d'attente (en millisecondes) pour que les données JavaScript se chargent sur le site (par défaut 20 000 ms).

## Exemple

Voici un exemple d'alerte envoyée sur Discord lorsque le retour dépasse 98% :

   ```bash
   Alerte : Le match Team A vs Team B dépasse 98% avec un retour de 100.5%
   ```

## Problèmes connus
Si le site cible change sa structure HTML, le script devra être ajusté.
Assurez-vous que le serveur sur lequel tourne le bot a une connexion stable à Internet et un accès au site de scraping.
Si le serveur redémarre, le bot s'arrête et ne se relance pas à moins d'avoir configuré un service dédié sur votre VPS.