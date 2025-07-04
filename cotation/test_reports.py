from appl import SiteWebLocal

print("--- DÉBUT DU TEST D'ENVOI D'EMAIL ---")

#SYMBOLS = ['BTCUSDT', 'SOLUSDT', 'ETHUSDT']
SYMBOLS = ['BTCUSDT']

RECIPIENT_EMAIL = 'test@local.com' # à remplacer par votre email

test_site = SiteWebLocal()

for symbol in SYMBOLS:
    test_site.send_report_email(
        symbol=symbol,  
        recipient_email=RECIPIENT_EMAIL,
    )

print("--- FIN DU TEST D'ENVOI D'EMAIL ---")
