# constants.py

# Seuil de pourcentage de retour
RETURN_THRESHOLD = 98.0

# Seuil de pourcentage maximal de retour
MAX_RETURN_THRESHOLD = 105.0

# URL du webhook Discord
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1287478753877823591/w5pgU1Xc6DRbKZ5wLztFJmc2wBJ9FxkjfHdM02GCKdO00CDMtqMo2mezCsw0pxh-aRlb'

# Textes
ALERT_MESSAGE_TEMPLATE = "Alerte : Le match **{match_name}** dépasse {threshold}% avec un retour de **{return_value}%**\n"
DISCORD_SUCCESS_MESSAGE = "Message envoyé sur Discord:\n{message}"
DISCORD_ERROR_MESSAGE = "Erreur lors de l'envoi du message sur Discord: {status_code}"
TIMEOUT_ERROR_MESSAGE = "Données JavaScript non chargées dans le délai imparti. Nouvelle tentative dans {minutes} minutes."

# Liste des codes HTTP OK
HTTP_SUCCESS_CODES = [200, 204]

# Nombre de minutes entre chaque vérification
CHECK_INTERVAL_MINUTES = 2

# Timeout pour attendre le chargement des données JavaScript (en millisecondes)
JS_LOAD_TIMEOUT = 20000

# Augmentation minimale du retour pour renvoyer une alerte (en pourcentage)
MIN_RETURN_INCREASE = 0.1
