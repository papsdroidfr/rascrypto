from cotations import BinanceAPI
from datetime import datetime, timedelta
from binance.client import Client
from analysis import TechnicalChartBuilder

import polars as pl


#cotations BTCUSDT récupérées depuis Binance
print("Récupération des cotations BTCUSDT...")
binance_api = BinanceAPI()
now = datetime.now()
start_date = now - timedelta(weeks=1); interval = Client.KLINE_INTERVAL_1HOUR
df = binance_api.get_historical_data(symbol='BTCUSDT', interval= interval, start_date_str=start_date.strftime('%d %b %Y %H:%M:%S'))
print (df)

# Analyse technique
print("Analyse technique des cotations BTCUSDT...")
builder = TechnicalChartBuilder()


df_ma = builder.add_moving_averages(df)
print("Moyennes mobiles ajoutées:", df_ma)
df_pivots = builder.add_pivot_levels(df_ma)
print("Niveaux de pivot ajoutés:", df_pivots)
df_analyzed = builder.add_oscillators(df_pivots)
print("Oscillateurs ajoutés:", df_analyzed)

stats = builder.add_summary_stats(df_analyzed)
print("Statistiques sommaires:", stats)
