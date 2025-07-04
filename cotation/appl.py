import os
import schedule
import time
import threading
import psutil
import plotly.graph_objects as go
import json


from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from binance.client import Client
from plotly.subplots import make_subplots

from pathlib import Path
from datetime import datetime, timedelta

from cotations import BinanceAPI
from scheduler import JobStore
from emailer import SimpleEmailer
from analysis import TechnicalChartBuilder
from info import CRYPTOS, PERIOD_SHORT, PERIOD_LONG, PERIOD_SUPPORT, TIME_SCHEDULER

    
class SiteWebLocal:
    """Classe principale pour l'application web locale de suivi des cryptomonnaies."""
    
    def __init__(self):
        # Initialisation de Flask et de sa configuration
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        self.app.secret_key = "une_cle_secrete_pour_les_messages_flash"
        
        # Initialisation des outils
        self.binance_api = BinanceAPI()
        self.db = JobStore()
        self.cryptos = CRYPTOS
        self.chart_builder = TechnicalChartBuilder()

        
        # Configuration des routes
        self.configurer_routes()

        
    def configurer_routes(self):
        self.app.route('/')(self.accueil)
        self.app.route('/dashboard')(self.dashboard_page)
        self.app.route('/monitoring')(self.monitoring_page)
        self.app.route('/scheduling', methods=['GET', 'POST'])(self.scheduling_page)
        self.app.route('/delete-schedule/<int:schedule_id>', methods=['POST'])(self.delete_schedule)
        self.app.route('/a-propos')(self.a_propos_page)
        self.app.route('/api/historique')(self.api_historique)
        self.app.route('/api/system-stats')(self.get_system_stats)


    def accueil(self):
        return redirect(url_for('dashboard_page'))
    

    def dashboard_page(self):
        return render_template('dashboard.html', titre="Dashboard Crypto", cryptos=self.cryptos)


    def monitoring_page(self):
        return render_template('monitoring.html', titre="Monitoring Système")


    def a_propos_page(self):
        return render_template('a_propos.html', titre="À Propos")
    
    
    def scheduling_page(self):
        """Page de planification des envois d'emails."""
        if request.method == 'POST':
            symbol, email, frequency = request.form['symbol'], request.form['recipient_email'], request.form['frequency']
            # On stocke en BDD.
            job_id = f"job_{os.urandom(8).hex()}"
            self.db.add_schedule(symbol, email, frequency, job_id)
            flash(f"Envoi programmé pour {symbol} vers {email} ({frequency}). Le serveur doit redémarrer pour appliquer le nouveau planning.", "success")
            return redirect(url_for('scheduling_page'))
        
        schedules = self.db.get_all_schedules()
        return render_template('scheduling.html', titre="Planification d'envois", schedules=schedules, cryptos=self.cryptos)


    def delete_schedule(self, schedule_id):
        """Supprime une tâche planifiée par son ID."""
        self.db.remove_schedule_by_id(schedule_id)
        flash("Tâche supprimée de la base. Redémarrez le serveur pour arrêter les envois.", "info")
        return redirect(url_for('scheduling_page'))


    def built_report(self, symbol: str, start_date_str: str, interval: str) -> tuple[Path | None, dict]:
        """Génère un rapport pour une crypto donnée et retourne le chemin de l'image générée ainsi que les stats."""
        
        df_raw = self.binance_api.get_historical_data(symbol, interval, start_date_str)
        
        # Analyse technique
        df_ma = self.chart_builder.add_moving_averages(df_raw, PERIOD_SHORT, PERIOD_LONG)
        df_pivots = self.chart_builder.add_pivot_levels(df_ma, PERIOD_SUPPORT)
        df_analyzed = self.chart_builder.add_oscillators(df_pivots)
        stats = self.chart_builder.add_summary_stats(df_analyzed)
        
        # Génération de l'image
        path = Path(f"temp/temp_chart_{symbol}_{os.urandom(4).hex()}.png")
        generated_path = self.chart_builder.generate_chart_image(df_analyzed, symbol, path)
        
        if generated_path:
            #print(f"Graphique généré avec succès : {generated_path}")
            return generated_path, stats
        else:
            print("Erreur lors de la génération du graphique.")
            return None, None
    
     
    def send_report_email(self, symbol, recipient_email) -> None:
        """Génère les graphiques sur 30j et 7 jours, et envoie l'email."""  
  
        print(f"TÂCHE EXÉCUTÉE : Génération du rapport pour {symbol} à destination de {recipient_email}...")

        # génération des graphiques sur 30j
        generated_path_30d, stats_30d = self.built_report(
            symbol=symbol,
            start_date_str='30 days ago UTC',
            interval=Client.KLINE_INTERVAL_4HOUR
        )
        
        # génération des graphiques sur 7j
        generated_path_7d, stats_7d = self.built_report(
            symbol=symbol,
            start_date_str='7 days ago UTC',
            interval=Client.KLINE_INTERVAL_1HOUR
        )

        # Vérification que les deux images ont bien été créées
        if not (generated_path_30d and generated_path_7d):
            print("Erreur: Au moins un des deux graphiques n'a pas pu être généré.")
            # Nettoyage au cas où un seul des deux aurait été créé
            if generated_path_30d and generated_path_30d.exists(): generated_path_30d.unlink()
            if generated_path_7d and generated_path_7d.exists(): generated_path_7d.unlink()
            return

        # --- Construction de l'e-mail enrichi ---
        sender_email = os.environ.get('GMAIL_USER')
        sender_pass = os.environ.get('GMAIL_APP_PASS')

        if not sender_email or not sender_pass:
            print("Erreur: GMAIL_USER ou GMAIL_APP_PASS n'est pas configuré.")
            return
        
        subject = f"Rapport Crypto {symbol} : 30j ({stats_30d['percent']:+.1f}%) | 7j ({stats_7d['percent']:+.1f}%)"
        image_paths = [str(generated_path_30d), str(generated_path_7d)]
        
        # Envoi et nettoyage
        try:
            emailer = SimpleEmailer(user=sender_email, password=sender_pass)
            html_body = emailer.build_report_html(symbol, stats_30d, stats_7d)
            emailer.send_html_with_images(recipient_email, subject, html_body, image_paths)
            print(f"Email rapports pour {symbol} envoyé avec succès à {recipient_email}.")
            
        except Exception as e:
            print(f"Échec de l'envoi de l'email : {e}")
            
        finally:
            generated_path_30d.unlink(missing_ok=True)
            generated_path_7d.unlink(missing_ok=True)
        


    def setup_schedules(self) -> None:
        """Lit la BDD et configure toutes les tâches avec la bibliothèque 'schedule'."""
        print("Configuration des tâches planifiées...")
        schedules = self.db.get_all_schedules()
        
        for schedule_item in schedules:
            
            symbol, email, freq = schedule_item[1], schedule_item[2], schedule_item[3]
            
            if freq == 'daily':
                schedule.every().day.at(TIME_SCHEDULER).do(self.send_report_email, symbol=symbol, recipient_email=email)
                
            elif freq == 'weekly':
                schedule.every().sunday.at(TIME_SCHEDULER).do(self.send_report_email, symbol=symbol, recipient_email=email)
            elif freq == 'monthly':
                schedule.every().month.on(1, TIME_SCHEDULER).do(self.send_report_email, symbol=symbol, recipient_email=email)
        
        print(f"{len(schedule.get_jobs())} tâches configurées.")


    def run_pending_tasks(self) -> None:
        """Boucle infinie qui exécute les tâches en attente. Tourne dans le thread principal."""
        print("Le scheduler est en marche et surveille les tâches...")
        while True:
            schedule.run_pending()
            # On attend un peu pour éviter de surcharger le CPU                
            time.sleep(1)
            


    def lancer(self, host='0.0.0.0', port=5000, use_reloader=False)-> None:
        """Orchestre le démarrage de l'application."""
        # On configure les tâches à partir de la BDD
        self.setup_schedules()

        # On lance le serveur Flask dans un thread d'arrière-plan
        print(f"Démarrage du serveur web sur http://{host}:{port}")
        flask_thread = threading.Thread(
            target=lambda: self.app.run(host=host, port=port, debug=False, use_reloader=False)
        )
        flask_thread.daemon = True
        flask_thread.start()

        # Le thread principal est dédié à la boucle du scheduler
        self.run_pending_tasks()


    def api_historique(self)-> jsonify:
        """ Endpoint API qui génère un graphique d'analyse technique pour une crypto donnée.
            Extrait les données, effectue l'analyse technique, et retourne le graphique au format JSON
        """
        try:
            # Récupération des paramètres de la requête
            symbol = request.args.get('crypto', 'BTCUSDC')
            profondeur = request.args.get('profondeur', '1m')
            
            # Logique pour start_date et interval
            now = datetime.now()
            interval = Client.KLINE_INTERVAL_4HOUR
            start_date = now - timedelta(days=30)
            if profondeur == '1j':
                start_date = now - timedelta(days=1); interval = Client.KLINE_INTERVAL_5MINUTE
            elif profondeur == '1s':
                start_date = now - timedelta(weeks=1); interval = Client.KLINE_INTERVAL_1HOUR
            elif profondeur == '1m':
                start_date = now - timedelta(days=30); interval = Client.KLINE_INTERVAL_4HOUR
            elif profondeur == '1a':
                start_date = now - timedelta(days=365); interval = Client.KLINE_INTERVAL_1DAY
            elif profondeur == '5a':
                start_date = now - timedelta(days=365*5); interval = Client.KLINE_INTERVAL_1WEEK

            # --- Récupération des données brutes ---
            df_raw = self.binance_api.get_historical_data(symbol, interval, str(start_date))
            if df_raw is None or df_raw.is_empty():
                return jsonify({'error': 'Impossible de récupérer les données.'})

            # --- Analyse technique ---
            df_ma = self.chart_builder.add_moving_averages(df_raw, PERIOD_SHORT, PERIOD_LONG)
            df_pivots = self.chart_builder.add_pivot_levels(df_ma, PERIOD_SUPPORT)
            df_analyzed = self.chart_builder.add_oscillators(df_pivots)
            
            summary_stats = self.chart_builder.add_summary_stats(df_analyzed)

            # --- Extraction des données en listes ---
            x_data = df_analyzed.get_column('Open Time').dt.strftime('%Y-%m-%dT%H:%M:%S').to_list()
            open_data = df_analyzed.get_column('Open').to_list()
            high_data = df_analyzed.get_column('High').to_list()
            low_data = df_analyzed.get_column('Low').to_list()
            close_data = df_analyzed.get_column('Close').to_list()
            volume_data = df_analyzed.get_column('Volume').to_list()
            ma_short_data = df_analyzed.get_column('MA_short').to_list()
            ma_long_data = df_analyzed.get_column('MA_long').to_list()
            rsi_data = df_analyzed.get_column('RSI_14').to_list()
            macd_line_data = df_analyzed.get_column('MACD_line').to_list()
            macd_signal_data = df_analyzed.get_column('MACD_signal').to_list()
            macd_hist_data = df_analyzed.get_column('MACD_hist').to_list()
            support_levels = df_analyzed.get_column("Support").drop_nulls().unique().to_list()
            resistance_levels = df_analyzed.get_column("Resistance").drop_nulls().unique().to_list()

            # --- Création de la figure pltolty avec 3 panneaux ---
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                row_heights=[0.65, 0.15, 0.20],
                specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}]]
            )

            # Panneau 1 : Prix (alimenté par les listes)
            fig.add_trace(go.Candlestick(x=x_data, open=open_data, high=high_data, low=low_data, close=close_data, name='Cours'), row=1, col=1)
            fig.add_trace(go.Scatter(x=x_data, y=ma_short_data, mode='lines', name='MA Courte', line={'color': 'orange'}), row=1, col=1)
            fig.add_trace(go.Scatter(x=x_data, y=ma_long_data, mode='lines', name='MA Longue', line={'color': 'purple'}), row=1, col=1)
            for level in support_levels: fig.add_hline(y=level, line_dash="dash", line_color="rgba(40, 167, 69, 0.7)", row=1, col=1)
            for level in resistance_levels: fig.add_hline(y=level, line_dash="dash", line_color="rgba(220, 53, 69, 0.7)", row=1, col=1)
            
            # Panneau 1 (bis) : Volume
            fig.add_trace(go.Bar(x=x_data, y=volume_data, name='Volume', marker_color='rgba(150,150,150,0.3)'), secondary_y=True, row=1, col=1)
            
            # Panneau 2 : RSI
            fig.add_trace(go.Scatter(x=x_data, y=rsi_data, name='RSI', line={'color': 'blue'}), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="rgba(239, 83, 80, 0.5)", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="rgba(38, 166, 154, 0.5)", row=2, col=1)

            # Panneau 3 : MACD
            fig.add_trace(go.Scatter(x=x_data, y=macd_line_data, name='MACD', line={'color': 'navy'}), row=3, col=1)
            fig.add_trace(go.Scatter(x=x_data, y=macd_signal_data, name='Signal', line={'color': 'cyan'}), row=3, col=1)
            fig.add_trace(go.Bar(x=x_data, y=macd_hist_data, name='Histogramme', marker_color='rgba(150,150,150,0.5)'), row=3, col=1)

            # --- Mise en forme finale et conversion JSON ---
            fig.update_layout(
                #title_text=f'Analyse Technique pour {self.cryptos.get(symbol, symbol)}',
                height=850,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_rangeslider_visible=False,
                yaxis=dict(title="Prix (USDC)"),
                yaxis2=dict(title="Volume", showgrid=False),
                yaxis3=dict(title="RSI"),
                yaxis4=dict(title="MACD")
            )
            
            graph_json = json.loads(fig.to_json())
            graph_json['summary_stats'] = summary_stats

            return jsonify(graph_json)

        except Exception as e:
            print(f"Erreur dans api_historique : {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Une erreur interne est survenue lors de la création du graphique.'})

    
    
    def get_system_stats(self)-> jsonify:
        """ Endpoint API qui retourne les statistiques système au format JSON. """
        # Usage CPU
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_cores_usage = psutil.cpu_percent(interval=None, percpu=True)

        # Température CPU
        temps = psutil.sensors_temperatures()
        cpu_temp = 0.0
        # La clé peut varier, on cherche celle du CPU du Pi
        if 'cpu_thermal' in temps:
            cpu_temp = temps['cpu_thermal'][0].current
        elif 'coretemp' in temps: # Pour d'autres systèmes Linux
            cpu_temp = temps['coretemp'][0].current

        # Usage RAM
        ram = psutil.virtual_memory()
        ram_total = ram.total / (1024**3) # Convertir en Go
        ram_used = ram.used / (1024**3)
        ram_percent = ram.percent

        # Usage Disque (pour la partition racine '/')
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024**3) # Convertir en Go
        disk_used = disk.used / (1024**3)
        disk_percent = disk.percent

        # On rassemble tout dans un dictionnaire
        stats = {
            'cpu_usage': cpu_usage,
            'cpu_cores_usage': cpu_cores_usage,
            'cpu_temp': round(cpu_temp, 1),
            'ram': {
                'total': round(ram_total, 2),
                'used': round(ram_used, 2),
                'percent': ram_percent
            },
            'disk': {
                'total': round(disk_total, 2),
                'used': round(disk_used, 2),
                'percent': disk_percent
            }
        }
        
        return jsonify(stats)    


if __name__ == '__main__':
    site = SiteWebLocal()
    site.lancer()