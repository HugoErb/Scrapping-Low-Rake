# constants.py

# URL du webhook Discord
DISCORD_WEBHOOK_URL = ''
COTEUR_URL = "https://www.coteur.com/comparateur-de-cotes"

# Textes
ALERT_MESSAGE_TEMPLATE = (
    "Le match **{match_name}** dépasse {threshold}% avec un retour de **{return_value}%**   "
    "({match_datetime}, {odds_display}).\n"
)
DISCORD_SUCCESS_MESSAGE = "Message envoyé sur Discord:\n{message}"
DISCORD_ERROR_MESSAGE = "Erreur lors de l'envoi du message sur Discord: {status_code}"
TIMEOUT_ERROR_MESSAGE = "Données JavaScript non chargées dans le délai imparti. Nouvelle tentative dans {minutes} minutes."

# Timeout pour attendre le chargement des données JavaScript (en millisecondes)
JS_LOAD_TIMEOUT = 20000

# Liste des codes HTTP OK
HTTP_SUCCESS_CODES = [200, 204]

# Seuil de pourcentage de retour
RETURN_THRESHOLD = 98.0

# Nombre de minutes entre chaque vérification
CHECK_INTERVAL_MINUTES = 5

# Nombre d'itérations après lesquelles on redémarre le navigateur Playwright
PLAYWRIGHT_SESSION_INTERVAL_ITERATION = 50

# Augmentation minimale du retour pour renvoyer une alerte (en pourcentage)
MIN_RETURN_INCREASE = 0.1

# Durée en heure après laquelle un match est supprimé de la liste des matchs alertés
LIST_EXPIRATION_HOURS = 12
