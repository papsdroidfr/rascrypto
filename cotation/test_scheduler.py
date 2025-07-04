import schedule
import time
from datetime import datetime

from appl import SiteWebLocal

# --- Étape de Préparation ---

def dummy_email_sender(symbol, recipient_email):
    """
    Ceci est notre fonction "mannequin". Elle remplace la vraie fonction d'envoi d'email.
    Elle ne fait qu'imprimer un message pour prouver qu'elle a été appelée.
    """
    print("-----------------------------------------------------")
    print(f"--- TÂCHE DÉCLENCHÉE à {datetime.now().strftime('%H:%M:%S')} ---")
    print(f"    -> Appel simulé pour envoyer le rapport de '{symbol}' à '{recipient_email}'.")
    print("-----------------------------------------------------\n")

def run_scheduler_test():
    """
    Fonction principale qui orchestre le test du scheduler.
    """
    print("--- Initialisation du test du scheduler ---")

    site = SiteWebLocal()

    # On remplace la vraie méthode par notre fonction mock
    site.send_report_email = dummy_email_sender

    # On vide les anciennes tâches et on charge la configuration depuis la BDD
    schedule.clear()
    site.setup_schedules()
    
    # On ajoute une tâche de test supplémentaire qui s'exécute très fréquemment
    # pour ne pas avoir à attendre 7h du matin pour voir un résultat.
    print("INFO: Ajout d'une tâche de test rapide qui s'exécute toutes les 15 secondes.")
    schedule.every(15).seconds.do(site.send_report_email, symbol="TEST-RAPIDE", recipient_email="test@local.com")

    # 5. On lance la boucle de surveillance du scheduler pendant une durée limitée
    print("\n--- Démarrage de la boucle du scheduler pour 65 secondes ---")
    print("Surveillez les messages de 'TÂCHE DÉCLENCHÉE' ci-dessous...")
    
    start_time = time.time()
    while time.time() - start_time < 65:  # La boucle tournera pendant 65 secondes
        schedule.run_pending()
        time.sleep(1) # Le scheduler vérifie chaque seconde s'il y a quelque chose à faire

    print("\n--- Test terminé ---")


if __name__ == "__main__":
    # On s'assure d'avoir au moins une tâche dans la BDD pour un test complet
    print("NOTE: Pour un test complet, assurez-vous d'avoir au moins une tâche")
    print("configurée via l'interface web (ex: un envoi quotidien).")
    run_scheduler_test()