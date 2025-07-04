import polars as pl
from polars import col
import mplfinance as mpf
from pathlib import Path


class TechnicalChartBuilder:
    """ Classe dédiée à la construction d'analyses techniques modulaires. """
    
    def add_summary_stats(self, df: pl.DataFrame) -> dict:
        """ Calcule et retourne un dictionnaire de statistiques de base pour la période."""
        
        if df is None or df.is_empty():
            return {}
            
        open_price = df.item(0, 'Open')
        close_price = df.item(-1, 'Close')
        diff = close_price - open_price
        
        return {
            "open": round(open_price, 2),
            "close": round(close_price, 2),
            "diff": round(diff, 2),
            "percent": round((diff / open_price) * 100, 2) if open_price != 0 else 0
        }
        
        
    def add_moving_averages(self, df: pl.DataFrame, short_window: int = 5, long_window: int = 50) -> pl.DataFrame:
        """ Ajoute des moyennes mobiles à un DataFrame de cotations. """   
        
        if df is None or df.is_empty():
            return df
            
        df = df.with_columns(
            pl.col("Close").rolling_mean(window_size=short_window, min_periods=1).alias("MA_short"),
            pl.col("Close").rolling_mean(window_size=long_window, min_periods=1).alias("MA_long")
        )
        return df
      
        
    def add_pivot_levels(self, df: pl.DataFrame, window_size: int = 10) -> pl.DataFrame:
        """Détecte les niveaux de support/résistance """
        
        if df is None or df.is_empty():
            return df

        # Condition pour être un support : le 'Low' est plus bas ou égal à tous
        # les 'Low' des 'window_size' périodes précédentes ET des 'window_size' périodes suivantes.
        is_support = pl.all_horizontal(
            # Crée une liste de conditions [Low <= Low-10, Low <= Low-9, ..., Low <= Low+9, Low <= Low+10]
            [pl.col("Low") <= pl.col("Low").shift(i) for i in range(-window_size, window_size + 1) if i != 0]
        )
        
        # Condition pour être une résistance : le 'High' est plus haut ou égal à tous
        # les 'High' des 'window_size' périodes précédentes ET des 'window_size' périodes suivantes.
        is_resistance = pl.all_horizontal(
            [pl.col("High") >= pl.col("High").shift(i) for i in range(-window_size, window_size + 1) if i != 0]
        )

        df =  df.with_columns(
            Support=pl.when(is_support).then(col("Low")).otherwise(None),
            Resistance=pl.when(is_resistance).then(col("High")).otherwise(None)
        )
        
        # On peut vouloir ne garder que les niveaux les plus pertinents pour éviter de surcharger le graph
        return df.with_columns(
            Support=col("Support").forward_fill(),
            Resistance=col("Resistance").forward_fill()
        )
        
        
    def add_oscillators(self, df: pl.DataFrame) -> pl.DataFrame:
        """Calcule et ajoute les colonnes RSI et MACD au DataFrame."""
        if df is None or df.is_empty():
            return df

        # Calcul du MACD
        fast_period, slow_period, signal_period = 12, 26, 9
        ema_fast = col("Close").ewm_mean(span=fast_period, adjust=False)
        ema_slow = col("Close").ewm_mean(span=slow_period, adjust=False)
        macd_line = (ema_fast - ema_slow).alias("MACD_line")
        signal_line = macd_line.ewm_mean(span=signal_period, adjust=False).alias("MACD_signal")
        histogram = (macd_line - signal_line).alias("MACD_hist")

        # Calcul du RSI
        rsi_length = 14
        price_diff = col("Close").diff(1)
        gains = pl.when(price_diff > 0).then(price_diff).otherwise(0)
        losses = pl.when(price_diff < 0).then(-price_diff).otherwise(0)
        avg_gain = gains.ewm_mean(alpha=1/rsi_length, adjust=False)
        avg_loss = losses.ewm_mean(alpha=1/rsi_length, adjust=False)
        relative_strength = (avg_gain / avg_loss).fill_null(0)
        rsi = (100 - (100 / (1 + relative_strength))).alias("RSI_14")

        return df.with_columns(macd_line, signal_line, histogram, rsi)
    

    def generate_chart_image(self, df_analyzed: pl.DataFrame, symbol: str, file_path: str) -> Path | None:
        """ Génère une image compacte du graphique avec les indicateurs techniques. """
        
        if df_analyzed is None or df_analyzed.is_empty():
            return None
            
        # 1. Calculs et préparation des données, pandas nécessaire pour mplfinance
        df_pandas = df_analyzed.to_pandas().set_index('Open Time')
        
        supports = df_pandas['Support'].dropna().unique().tolist()
        resistances = df_pandas['Resistance'].dropna().unique().tolist()
        hlines = dict(hlines=supports + resistances, 
                      colors=['g'] * len(supports) + ['r'] * len(resistances), 
                      linestyle='--')

        # Préparation des tracés additionnels
        additional_plots = []
        
        # Moyennes Mobiles (panel 0)
        if 'MA_short' in df_pandas.columns and not df_pandas['MA_short'].isnull().all():
            additional_plots.append(mpf.make_addplot(df_pandas['MA_short'], color='orange'))
        if 'MA_long' in df_pandas.columns and not df_pandas['MA_long'].isnull().all():
            additional_plots.append(mpf.make_addplot(df_pandas['MA_long'], color='purple'))
        
        # Volume (panel 0, axe Y secondaire)
        if 'Volume' in df_pandas.columns:
            additional_plots.append(mpf.make_addplot(df_pandas['Volume'], type='bar', panel=0, color='gray', alpha=0.3, secondary_y=True))

        next_panel = 1

        # RSI (panel 1)
        if 'RSI_14' in df_pandas.columns and not df_pandas['RSI_14'].isnull().all():
            additional_plots.append(mpf.make_addplot(df_pandas['RSI_14'], panel=next_panel, color='blue', ylabel='RSI'))
            next_panel += 1

        # MACD (panel 2)
        if 'MACD_line' in df_pandas.columns and not df_pandas['MACD_line'].isnull().all():
            macd_plots = [
                mpf.make_addplot(df_pandas['MACD_line'], panel=next_panel, color='navy', ylabel='MACD'),
                mpf.make_addplot(df_pandas['MACD_signal'], panel=next_panel, color='cyan'),
                mpf.make_addplot(df_pandas['MACD_hist'], type='bar', panel=next_panel, color='gray', alpha=0.5)
            ]
            additional_plots.extend(macd_plots)
            next_panel += 1

        # 3. Génération du graphique
        try:
            image_path = Path(file_path)
            image_path.parent.mkdir(parents=True, exist_ok=True)
            
            panel_ratios_list = (6, 2, 2)
            
            mpf.plot(
                df_pandas,
                type='candle', style='yahoo', title=f'\nAnalyse Technique {symbol}',
                ylabel='Cours (USDC)',
                volume=False,
                addplot=additional_plots if additional_plots else None,
                panel_ratios=panel_ratios_list,
                hlines=hlines, figratio=(12, 8), figscale=1.2,
                savefig=str(image_path)
            )
            
            #print(f"Image compacte générée avec succès via Matplotlib : {image_path}")
            return image_path
            
        except Exception as e:
            print(f"Erreur lors de la génération de l'image avec Matplotlib : {e}")
            import traceback
            traceback.print_exc()
            return None