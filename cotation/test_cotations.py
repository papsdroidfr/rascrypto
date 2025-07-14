from cotations import BinanceAPI
from datetime import datetime, timedelta
from binance.client import Client

# Exemple d'utilisation de la classe BinanceAPI pour récupérer des données historiques
binance_api = BinanceAPI()
now = datetime.now()
start_date = now - timedelta(weeks=1); interval = Client.KLINE_INTERVAL_1HOUR
df = binance_api.get_historical_data(symbol='BTCUSDT', interval= interval, start_date_str=start_date.strftime('%d %b %Y %H:%M:%S'))

print (df.head())

