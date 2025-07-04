import polars as pl
from binance.client import Client


class BinanceAPI:
    """Gère la communication avec l'API de Binance pour récupérer les données de marché"""
    
    def __init__(self) -> None:
        self.client = Client()

    def get_historical_data(self, symbol, interval, start_date_str) -> pl.DataFrame | None:
        """Récupère les données OHLCV brutes depuis Binance."""
        
        try:
            klines = self.client.get_historical_klines(symbol, interval, start_date_str)
            if not klines: return None

            df = pl.DataFrame({
                "Open Time": [r[0] for r in klines], "Open": [r[1] for r in klines],
                "High": [r[2] for r in klines], "Low": [r[3] for r in klines],
                "Close": [r[4] for r in klines], "Volume": [r[5] for r in klines]
            })

            # On se contente de convertir les types de données.
            df = df.with_columns(
                pl.col("Open Time").cast(pl.Datetime(time_unit="ms")),
                pl.col("Open").cast(pl.Float64),
                pl.col("High").cast(pl.Float64),
                pl.col("Low").cast(pl.Float64),
                pl.col("Close").cast(pl.Float64),
                pl.col("Volume").cast(pl.Float64)
            )
            return df
        
        except Exception as e:
            print(f"Erreur lors de la récupération des données pour {symbol}: {e}")
            return None
