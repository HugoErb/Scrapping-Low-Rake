from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from discord_webhook import DiscordWebhook
import time
from constants import *  # Importer toutes les constantes

# Dictionnaire pour stocker les matchs déjà alertés avec leur dernier pourcentage de retour
alerted_matches = {}

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
        print(DISCORD_SUCCESS_MESSAGE.format(message=message))
    else:
        print(DISCORD_ERROR_MESSAGE.format(status_code=response.status_code))

def scrape_cotes():
    """
    Scrape les cotes des matchs sur le site web "coteur.com".
    Vérifie si les cotes ont dépassé un seuil (RETURN_THRESHOLD), et envoie une alerte si nécessaire.
    Si un match a déjà été alerté, une nouvelle alerte est envoyée seulement si le retour a augmenté d'au moins MIN_RETURN_INCREASE%.

    Returns:
        None: Envoie des messages d'alerte sur Discord si les conditions sont remplies.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Naviguer vers l'URL
            page.goto("https://www.coteur.com/comparateur-de-cotes")

            # Attendre que les données JavaScript soient chargées (avec timeout configurable)
            page.wait_for_selector('span[data-controller="retour"]', timeout=JS_LOAD_TIMEOUT)

            # Récupérer tous les matchs
            matches = page.query_selector_all('div.events.d-flex.flex-column.flex-sm-row.flex-wrap')

            alert_message = ""  # Initialiser un message vide pour collecter toutes les alertes

            for match in matches:
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
                        if MAX_RETURN_THRESHOLD >= cote_value >= RETURN_THRESHOLD:
                            # Vérifier si le match a déjà été alerté et si le retour a augmenté suffisamment
                            if match_name in alerted_matches:
                                last_return_value = alerted_matches[match_name]
                                if cote_value >= last_return_value + MIN_RETURN_INCREASE:
                                    alert_message += ALERT_MESSAGE_TEMPLATE.format(
                                        match_name=match_name, threshold=RETURN_THRESHOLD, return_value=cote_value
                                    )
                                    # Mettre à jour le retour du match
                                    alerted_matches[match_name] = cote_value
                            else:
                                # Alerter pour la première fois et stocker le retour du match
                                alert_message += ALERT_MESSAGE_TEMPLATE.format(
                                    match_name=match_name, threshold=RETURN_THRESHOLD, return_value=cote_value
                                )
                                alerted_matches[match_name] = cote_value

                    except ValueError:
                        print(f"Impossible de convertir la cote pour le match {match_name}")

            if alert_message:
                # Ajouter le lien à la fin du message
                alert_message += ALERT_FOOTER

                # Envoyer toutes les alertes dans un seul message
                envoyer_alerte_discord(alert_message)

        except PlaywrightTimeoutError:
            # Gestion de l'erreur si les données JavaScript ne sont pas chargées dans le délai imparti
            print(TIMEOUT_ERROR_MESSAGE.format(minutes=CHECK_INTERVAL_MINUTES))
        
        finally:
            browser.close()

# Boucle pour récupérer les données toutes les CHECK_INTERVAL_MINUTES minutes
while True:
    try:
        scrape_cotes()
    except Exception as e:
        # Capture et gestion de toutes les erreurs
        print(f"Une erreur est survenue : {str(e)}. Nouvelle tentative dans {CHECK_INTERVAL_MINUTES} minutes.")
    
    print(f"Attente de {CHECK_INTERVAL_MINUTES} minutes avant la prochaine vérification...")
    time.sleep(CHECK_INTERVAL_MINUTES * 60)  # Conversion en secondes
