from playwright.sync_api import sync_playwright
from discord_webhook import DiscordWebhook
import time

# Constante : seuil de pourcentage de retour
RETURN_THRESHOLD = 98.0

# Liste des matchs pour lesquels l'alerte a déjà été levée
alerted_matches = set()

# URL du webhook Discord
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1286997439081086976/JFpf97871cWtOiXLqxxby-yeoAciijdZEkw8xmhWxSfqjCYGRG6h_rxX8X091FnUW-kF'

def envoyer_alerte_discord(message):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, content=message)
    response = webhook.execute()
    if response.status_code in [200,204]:
        print(f"Message envoyé sur Discord:\n{message}")
    else:
        print(f"Erreur lors de l'envoi du message sur Discord: {response.status_code}")


def scrape_cotes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Naviguer vers l'URL
        page.goto("https://www.coteur.com/comparateur-de-cotes")

        # Attendre que les données JavaScript soient chargées
        page.wait_for_selector('span[data-controller="retour"]', timeout=20000)  # Attend jusqu'à 20 secondes

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

            # Vérifier si ce match a déjà été alerté
            if match_name in alerted_matches:
                continue  # On passe au prochain match si l'alerte a déjà été levée

            # Extraction du pourcentage de retour
            retour_element = match.query_selector('span[data-controller="retour"]')
            if retour_element:
                cote_text = retour_element.inner_text().replace('%', '').replace(',', '.').strip()
                try:
                    cote_value = float(cote_text)
                    if cote_value > RETURN_THRESHOLD:  # Utilisation du seuil défini
                        alert_message += f"Alerte : Le match {match_name} dépasse {RETURN_THRESHOLD}% avec un retour de {cote_value}%\n"

                        # Ajouter le match à la liste des alertes
                        alerted_matches.add(match_name)
                except ValueError:
                    print(f"Impossible de convertir la cote pour le match {match_name}")

        if alert_message:
            # Ajouter le lien à la fin du message
            alert_message += "\nVoir sur : https://www.coteur.com/comparateur-de-cotes"

            # Envoyer toutes les alertes dans un seul message
            envoyer_alerte_discord(alert_message)

        browser.close()


# Boucle pour récupérer les données toutes les 5 minutes
while True:
    scrape_cotes()
    print("Attente de 5 minutes avant la prochaine vérification...")
    time.sleep(300)  # 300 secondes = 5 minutes
