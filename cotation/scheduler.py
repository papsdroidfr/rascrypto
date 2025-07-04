import sqlite3

class JobStore:
    """
    Gère le stockage et la récupération des tâches planifiées
    dans une base de données SQLite.
    """
    def __init__(self, db_path='scheduler.db'):
        """
        Initialise la connexion à la base de données et crée la table si elle n'existe pas.
        """
        self.db_path = db_path
        # check_same_thread=False est important pour une utilisation avec Flask
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.init_db()

    def init_db(self):
        """Crée la table 'schedules' si elle n'existe pas déjà."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                frequency TEXT NOT NULL,
                job_id TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def get_all_schedules(self):
        """Récupère toutes les tâches planifiées depuis la base de données."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM schedules ORDER BY id DESC")
        return cursor.fetchall()

    def add_schedule(self, symbol, email, frequency, job_id):
        """
        Ajoute une nouvelle tâche à la base de données.
        L'ID de la ligne est géré automatiquement par SQLite.
        """
        sql = "INSERT INTO schedules (symbol, recipient_email, frequency, job_id) VALUES (?, ?, ?, ?)"
        params = (symbol, email, frequency, job_id)
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            print(f"INFO: Tâche pour {symbol} ajoutée à la base de données avec succès.")
        except sqlite3.Error as e:
            # Affiche une erreur claire si l'insertion échoue
            print(f"ERREUR BDD lors de l'ajout de la tâche : {e}")

    def remove_schedule_by_id(self, schedule_id):
        """Supprime une tâche de la base de données en utilisant son ID de ligne."""
        sql = "DELETE FROM schedules WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (schedule_id,))
            self.conn.commit()
            print(f"INFO: Tâche avec id={schedule_id} supprimée de la base de données.")
        except sqlite3.Error as e:
            print(f"ERREUR BDD lors de la suppression de la tâche (id={schedule_id}): {e}")

    def __del__(self):
        """Ferme la connexion à la base de données lorsque l'objet est détruit."""
        if self.conn:
            self.conn.close()