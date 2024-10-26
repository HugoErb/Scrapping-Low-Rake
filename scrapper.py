import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from discord_webhook import DiscordWebhook
import time
from datetime import datetime, timedelta
from constants import *  # Importer toutes les constantes

# Configuration du module logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='[%(asctime)s] %(levelname)s : %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

# Dictionnaire pour stocker les matchs déjà alertés avec leur dernier pourcentage de retour et l'heure de l'alerte
alerted_matches = {}

def log_message(message, level="info"):
    """
    Affiche un message avec la date et l'heure actuelle, et enregistre dans les logs avec le niveau spécifié.

    Args:
        message (str): Le message à enregistrer dans les logs.
        level (str): Le niveau de log ("info", "error", "debug", etc.). Par défaut "info".

    Returns:
        None
    """
    logger = {
        "info": logging.info,
        "error": logging.error,
        "debug": logging.debug,
    }.get(level, logging.info)
    
    if level != "info":
        logger(f"{message}")


def envoyer_alerte_discord(message):
    """
    Envoie un message d'alerte sur un canal Discord via un webhook.

    Args:
        message (str): Le message à envoyer via le webhook Discord.

    Returns:
        None: Le résultat de l'envoi est imprimé dans la console,
        avec un succès ou un message d'erreur en fonction du code HTTP de la réponse.
    """
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, content=message)
    response = webhook.execute()
    if response.status_code in HTTP_SUCCESS_CODES:
        log_message(DISCORD_SUCCESS_MESSAGE.format(message=message), "info")
    else:
        log_message(DISCORD_ERROR_MESSAGE.format(status_code=response.status_code), "error")


def clean_old_alerts():
    """
    Supprime les matchs du dictionnaire des alertes si l'alerte a plus de ALERT_EXPIRATION_HOURS heures.

    Args:
        None

    Returns:
        None: Les alertes expirées sont supprimées du dictionnaire alerted_matches.
    """
    current_time = datetime.now()
    matches_to_remove = []

    for match_name, (alert_time, return_value) in alerted_matches.items():
        if current_time - alert_time > timedelta(hours=LIST_EXPIRATION_HOURS):
            matches_to_remove.append(match_name)

    # Suppression des matchs obsolètes
    for match_name in matches_to_remove:
        del alerted_matches[match_name]
    log_message(f"Matchs supprimés du dictionnaire : {matches_to_remove}", "debug")
    log_message(f"Matchs  du dictionnaire : {alerted_matches}", "debug")


def scrape_cotes(page):
    """
    Scrape les cotes des matchs sur le site web "coteur.com".
    Si un match atteint un seuil de retour ou que le retour augmente suffisamment, une alerte est envoyée.

    Args:
        page (Page): La page Playwright utilisée pour effectuer le scraping.

    Returns:
        None: Les alertes sont envoyées si les conditions sont remplies, et les erreurs sont gérées.
    """
    try:
        # Naviguer vers l'URL
        page.goto("https://www.coteur.com/comparateur-de-cotes")

        # Attendre que les données JavaScript soient chargées (avec timeout configurable)
        page.wait_for_selector('span[data-controller="retour"]', timeout=JS_LOAD_TIMEOUT)

        # Récupérer tous les matchs
        matches = page.query_selector_all('div.events.d-flex.flex-column.flex-sm-row.flex-wrap')

        alert_message = ""  # Initialiser un message vide pour collecter toutes les alertes

        for match in matches:
            # Extraction de la date et de l'heure du match
            match_datetime = extract_match_datetime(match)
            if not match_datetime:
                log_message("Impossible d'extraire la date/heure du match.", "error")
                continue  # Passer au match suivant si la date/heure n'est pas valide

            # Vérification si le match a déjà commencé
            if match_datetime < datetime.now():
                log_message(f"Le match {match_name} a déjà commencé, aucune alerte envoyée.", "info")
                continue

            # Extraction des équipes
            team_elements = match.query_selector_all('div.event-team')
            if len(team_elements) == 2:
                team1 = team_elements[0].inner_text().strip()
                team2 = team_elements[1].inner_text().strip()
                match_name = f"{team1} vs {team2}"

            # Extraction du pourcentage de retour
            retour_element = match.query_selector('span[data-controller="retour"]')
            if retour_element:
                cote_text = retour_element.inner_text().replace('%', '').replace(',', '.').strip()
                try:
                    cote_value = float(cote_text)
                    # Vérification des conditions pour envoyer une alerte
                    if cote_value >= RETURN_THRESHOLD:

                        if match_name in alerted_matches:
                            alert_time, last_return_value = alerted_matches[match_name]
                            if cote_value >= last_return_value + MIN_RETURN_INCREASE:
                                alert_message += ALERT_MESSAGE_TEMPLATE.format(
                                    match_name=match_name, threshold=RETURN_THRESHOLD, return_value=cote_value
                                )
                                # Mettre à jour l'heure et le retour du match
                                alerted_matches[match_name] = (datetime.now(), cote_value)
                        else:
                            # Alerter pour la première fois et stocker le retour du match avec l'heure
                            alert_message += ALERT_MESSAGE_TEMPLATE.format(
                                match_name=match_name, threshold=RETURN_THRESHOLD, return_value=cote_value
                            )
                            alerted_matches[match_name] = (datetime.now(), cote_value)

                except ValueError:
                    log_message(f"Impossible de convertir la cote pour le match {match_name}", "error")

        if alert_message:
            # Envoyer toutes les alertes dans un seul message
            envoyer_alerte_discord(alert_message)

    except PlaywrightTimeoutError:
        # Gestion de l'erreur si les données JavaScript ne sont pas chargées dans le délai imparti
        log_message(TIMEOUT_ERROR_MESSAGE.format(minutes=CHECK_INTERVAL_MINUTES), "error")


def extract_match_datetime(match):
    """
    Extrait la date et l'heure d'un match à partir de l'élément HTML.

    Args:
        match (ElementHandle): L'élément HTML du match.

    Returns:
        datetime: La date et l'heure du match, ou None si l'extraction échoue.
    """
    try:
        # Extraction de l'élément contenant la date et l'heure du match
        time_element = match.query_selector('div.event-time')
        if time_element:
            # Format attendu: "11/10\n04:00" -> "11/10 04:00"
            date_time_str = time_element.inner_text().replace("\n", " ").strip()
            # Ajout de l'année actuelle pour former une date complète
            date_time_obj = datetime.strptime(f"{date_time_str} {datetime.now().year}", "%d/%m %H:%M %Y")
            return date_time_obj
    except Exception as e:
        log_message(f"Erreur lors de l'extraction de la date/heure du match: {str(e)}", "error")
    return None


def main():
    """
    Fonction principale qui gère l'exécution du scraping et la session Playwright.

    Args:
        None

    Returns:
        None: Le scraping est effectué à intervalles réguliers et les alertes sont envoyées.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Boucle pour récupérer les données toutes les CHECK_INTERVAL_MINUTES minutes
        while True:
            try:
                scrape_cotes(page)
            except Exception as e:
                # Capture et gestion de toutes les erreurs
                log_message(
                    f"Une erreur est survenue : {str(e)}. Nouvelle tentative dans {CHECK_INTERVAL_MINUTES} minutes.",
                    "error")

            clean_old_alerts()
            log_message(f"Prochaine vérification dans {CHECK_INTERVAL_MINUTES} minutes.", "info")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)  # Conversion en secondes


if __name__ == "__main__":
    main()
