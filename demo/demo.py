import os
from flask import Flask, render_template, request, redirect, url_for

class SiteWebLocal:
    """
    Classe principale pour configurer et lancer l'application web Flask.
    """
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)  # Nécessaire pour les messages flash
        self.configurer_routes()

    def configurer_routes(self):
        """
        Définit toutes les routes de l'application.
        """
        self.app.add_url_rule('/', 'accueil', self.accueil)
        self.app.add_url_rule('/a-propos', 'a_propos', self.a_propos)
        self.app.add_url_rule('/contact', 'contact', self.contact, methods=['GET', 'POST'])
        self.app.add_url_rule('/merci', 'merci', self.merci)

    def accueil(self):
        """Affiche la page d'accueil."""
        return render_template('accueil.html', titre="Accueil")

    def a_propos(self):
        """Affiche la page 'À propos'."""
        return render_template('a_propos.html', titre="À Propos")

    def contact(self):
        """Affiche le formulaire de contact et traite les données soumises."""
        if request.method == 'POST':
            # Ici, vous pourriez traiter les données du formulaire (ex: les enregistrer)
            nom = request.form.get('nom')
            email = request.form.get('email')
            message = request.form.get('message')
            print(f"Nouveau message de {nom} ({email}):\n{message}")
            return redirect(url_for('merci'))
        return render_template('contact.html', titre="Contact")

    def merci(self):
        """Affiche la page de remerciement après soumission du formulaire."""
        return render_template('merci.html', titre="Merci")

    def lancer(self, host='127.0.0.1', port=5000):
        """
        Lance le serveur de développement Flask.
        Le site sera accessible uniquement sur votre réseau local.
        """
        self.app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    site = SiteWebLocal()
    site.lancer()