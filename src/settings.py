import os
import sqlite3

DB_NAME = os.getenv("DB_NAME", default="bot.db")
DEFAULT_WRAPPING = os.getenv("DEFAULT_WRAPPING", default="[[*]]")


class BotSettings:
    def __init__(self):
        self.conn = sqlite3.connect(f"../{DB_NAME}")
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings
            (server_id text UNIQUE, wrapping text)    
        """
        )
        self.conn.commit()

    def set_wrapping(self, server_id, wrapping):
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO settings
            (server_id, wrapping)
            VALUES(?, ?)
        """,
            (server_id, DEFAULT_WRAPPING),
        )

        self.cursor.execute(
            """
            UPDATE settings
            SET wrapping=?
            WHERE server_id=?
        """,
            (wrapping, server_id),
        )

        self.conn.commit()

    def get_wrapping(self, server_id):
        self.cursor.execute(
            "SELECT wrapping FROM settings WHERE server_id=?", (server_id,)
        )
        result = self.cursor.fetchone()

        if result is not None:
            return result[0]
        else:
            return DEFAULT_WRAPPING


bot_settings = BotSettings()
