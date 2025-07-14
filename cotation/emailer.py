import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import make_msgid

class SimpleEmailer:
    """ Classe pour envoyer des emails avec des rapports en HTML. """
    
    def __init__(self, smtp_server='smtp.gmail.com', smtp_port=465, user=None, password=None) -> None:
        """ Initialise le client email avec les paramètres SMTP et les identifiants de l'utilisateur."""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.user = user or os.environ.get('GMAIL_USER')
        self.password = password or os.environ.get('GMAIL_APP_PASS')
        
    def build_report_html(self, symbol, stats_30d, stats_7d)-> str:
        """ Génère le corps HTML du rapport avec les statistiques et les graphiques."""
        
        color_30d = "#26a69a" if stats_30d['diff'] >= 0 else "#ef5350"
        sign_30d = "+" if stats_30d['diff'] >= 0 else ""
        color_7d = "#26a69a" if stats_7d['diff'] >= 0 else "#ef5350"
        sign_7d = "+" if stats_7d['diff'] >= 0 else ""
        
        html_body = f"""
        <html>
            <body style="font-family: sans-serif; color: #333;">
                <p>Bonjour,</p>
                <p>Voici votre rapport crypto pour <strong>{symbol}</strong> avec deux perspectives :</p>
                
                <h2 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">Analyse sur 30 jours</h2>
                <table style="margin-bottom: 25px;">
                    <tr><td style="padding: 4px;">Ouverture :</td><td style="padding: 4px;">{stats_30d['open']:.2f} USDC</td></tr>
                    <tr><td style="padding: 4px;">Fermeture :</td><td style="padding: 4px;">{stats_30d['close']:.2f} USDC</td></tr>
                    <tr style="font-weight: bold; color: {color_30d};"><td style="padding: 4px;">Variation :</td><td style="padding: 4px;">{sign_30d}{stats_30d['diff']:.2f} USDC ({sign_30d}{stats_30d['percent']:.2f} %)</td></tr>
                    <tr><td style="padding: 4px;">RSI fermeture :</td><td style="padding: 4px;">{stats_30d['rsi']:.2f} %</td></tr>
                </table>
                <img src="{{img0}}"><br><br>

                <h2 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">Analyse sur 7 jours</h2>
                <table style="margin-bottom: 25px;">
                    <tr><td style="padding: 4px;">Ouverture :</td><td style="padding: 4px;">{stats_7d['open']:.2f} USDC</td></tr>
                    <tr><td style="padding: 4px;">Fermeture :</td><td style="padding: 4px;">{stats_7d['close']:.2f} USDC</td></tr>
                    <tr style="font-weight: bold; color: {color_7d};"><td style="padding: 4px;">Variation :</td><td style="padding: 4px;">{sign_7d}{stats_7d['diff']:.2f} USDC ({sign_7d}{stats_7d['percent']:.2f} %)</td></tr>
                    <tr><td style="padding: 4px;">RSI fermeture:</td><td style="padding: 4px;">{stats_7d['rsi']:.2f} %</td></tr>
                </table>
                <img src="{{img1}}">

                <p style="margin-top: 30px;">Cordialement,<br>Votre Serveur RasCrypto.</p>
            </body>
        </html>
        """
        return html_body

    def send_html_with_images(self, to, subject, html_body, image_paths) -> None:
        """ Envoie un email HTML avec des images attachées. """
        
        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = self.user
        msg['To'] = to

        # Génère un Content-ID unique pour chaque image et remplace dans le HTML
        cids = [make_msgid()[1:-1] for _ in image_paths]
        for i, cid in enumerate(cids):
            html_body = html_body.replace(f'{{img{i}}}', f'cid:{cid}')
        msg.attach(MIMEText(html_body, "html"))

        # Ajoute les images
        for i, (img_path, cid) in enumerate(zip(image_paths, cids)):
            with open(img_path, 'rb') as fp:
                img = MIMEImage(fp.read())
                img.add_header('Content-ID', f'<{cid}>')
                msg.attach(img)

        # Envoi
        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as smtp:
            smtp.login(self.user, self.password)
            smtp.send_message(msg)