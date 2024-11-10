import logging
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from discord_webhook import DiscordWebhook
from datetime import datetime, timedelta
from constants import *  # Importer toutes les constantes

# Configuration du module logging
logging.basicConfig(
    level=logging.INFO, 
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
    # Sélectionne la fonction de log en fonction du niveau spécifié
    logger = {
        "info": logging.info,
        "error": logging.error,
        "debug": logging.debug,
    }.get(level, logging.info)
    logger(f"{message}")

async def envoyer_alerte_discord(message):
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
    # Identifie les matchs qui ont dépassé le délai d'expiration
    current_time = datetime.now()
    matches_to_remove = []
    for match_name, (alert_time, return_value) in alerted_matches.items():
        if current_time - alert_time > timedelta(hours=LIST_EXPIRATION_HOURS):
            matches_to_remove.append(match_name)
    # Supprime les matchs obsolètes
    for match_name in matches_to_remove:
        del alerted_matches[match_name]
    log_message(f"Matchs supprimés du dictionnaire : {matches_to_remove}", "debug")

async def scrape_cotes(page):
    try:
        await page.goto(COTEUR_URL)
        await page.wait_for_selector('span[data-controller="retour"]', timeout=JS_LOAD_TIMEOUT)
        matches = await page.query_selector_all('div.events.d-flex.flex-column.flex-sm-row.flex-wrap')
        alert_message = ""

        for match in matches:
            # Initialiser les variables nécessaires
            match_name = None
            odds_display = ""

            # Extraction de la date et heure du match
            match_datetime = await extract_match_datetime(match)
            if not match_datetime or match_datetime < datetime.now():
                continue  # Ignore le match si la date est invalide ou si le match est déjà commencé

            # Extraction des équipes
            team_elements = await match.query_selector_all('div.event-team')
            if len(team_elements) == 2:
                team1 = (await team_elements[0].inner_text()).strip()
                team2 = (await team_elements[1].inner_text()).strip()
                match_name = f"{team1} vs {team2}"

            # Extraction des cotes (victoire équipe 1, match nul, victoire équipe 2)
            odds_elements = await match.query_selector_all('div.event-odd strong[data-odd-target="odds"]')
            if len(odds_elements) >= 2:  # Vérifie qu'il y a au moins deux cotes (évite les erreurs)
                team1_odds = (await odds_elements[0].inner_text()).strip()
                team2_odds = (await odds_elements[1].inner_text()).strip()

                # Si la cote du match nul existe, l'inclure dans l'affichage
                if len(odds_elements) > 2:
                    draw_odds = (await odds_elements[2].inner_text()).strip()
                    odds_display = f"**{team1_odds}** - **{draw_odds}** - **{team2_odds}**"
                else:
                    odds_display = f"**{team1_odds}** - **{team2_odds}**"

            # Vérifie que match_name a bien été défini avant de continuer
            if match_name is None:
                log_message("Informations de match incomplètes, alerte ignorée.", "debug")
                continue

            # Extraction du retour
            retour_element = await match.query_selector('span[data-controller="retour"]')
            if retour_element:
                cote_text = (await retour_element.inner_text()).replace('%', '').replace(',', '.').strip()
                try:
                    cote_value = float(cote_text)
                    if cote_value >= RETURN_THRESHOLD:
                        if match_name in alerted_matches:
                            alert_time, last_return_value = alerted_matches[match_name]
                            if cote_value >= last_return_value + MIN_RETURN_INCREASE:
                                alert_message += ALERT_MESSAGE_TEMPLATE.format(
                                    match_name=match_name,
                                    threshold=RETURN_THRESHOLD,
                                    return_value=cote_value,
                                    match_datetime=match_datetime.strftime("%d/%m %Hh%M"),
                                    odds_display=odds_display
                                )
                                alerted_matches[match_name] = (datetime.now(), cote_value)
                        else:
                            alert_message += ALERT_MESSAGE_TEMPLATE.format(
                                match_name=match_name,
                                threshold=RETURN_THRESHOLD,
                                return_value=cote_value,
                                match_datetime=match_datetime.strftime("%d/%m %Hh%M"),
                                odds_display=odds_display
                            )
                            alerted_matches[match_name] = (datetime.now(), cote_value)
                except ValueError:
                    log_message(f"Impossible de convertir la cote pour le match {match_name}", "error")
        
        if alert_message:
            await envoyer_alerte_discord(alert_message)
        
        return True

    except (PlaywrightTimeoutError, Exception) as e:
        log_message(f"Erreur de scraping ou fermeture de page/navigateur: {str(e)}", "error")
        return False

async def extract_match_datetime(match):
    """
    Extrait la date et l'heure d'un match à partir de l'élément HTML.

    Args:
        match (ElementHandle): L'élément HTML du match.

    Returns:
        datetime: La date et l'heure du match, ou None si l'extraction échoue.
    """
    try:
        # Extrait l'élément contenant la date et l'heure du match
        time_element = await match.query_selector('div.event-time')
        if time_element:
            # Format attendu: "11/10\n04:00" -> "11/10 04:00"
            date_time_str = (await time_element.inner_text()).replace("\n", " ").strip()
            # Ajoute l'année actuelle pour former une date complète
            date_time_obj = datetime.strptime(f"{date_time_str} {datetime.now().year}", "%d/%m %H:%M %Y")
            return date_time_obj
    except Exception as e:
        log_message(f"Erreur lors de l'extraction de la date/heure du match: {str(e)}", "error")
    return None

async def main():
    """
    Fonction principale qui gère l'exécution du scraping et la session Playwright.

    Args:
        None

    Returns:
        None: Le scraping est effectué à intervalles réguliers et les alertes sont envoyées.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        iteration_count = 0
        while True:
            try:
                success = await scrape_cotes(page)
                
                # Vérifie si le scraping a échoué, auquel cas on redémarre le navigateur
                if not success:
                    await page.close()
                    await browser.close()
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    iteration_count = 0  # Réinitialise le compteur

                clean_old_alerts()
                log_message(f"Prochaine vérification dans {CHECK_INTERVAL_MINUTES} minutes.", "info")

                # Compteur pour redémarrer le navigateur périodiquement
                iteration_count += 1
                if iteration_count >= PLAYWRIGHT_SESSION_INTERVAL_ITERATION:
                    await page.close()
                    await browser.close()
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    iteration_count = 0

            except Exception as e:
                log_message(f"Une erreur est survenue dans la boucle principale : {str(e)}. Nouvelle tentative dans {CHECK_INTERVAL_MINUTES} minutes.", "error")

            await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)

# Exécution du script principal en mode asynchrone
if __name__ == "__main__":
    asyncio.run(main())
