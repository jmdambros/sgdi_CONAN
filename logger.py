import sqlite3
from datetime import datetime

DB_PATH = 'demandas.db'

def log_action(usuario, acao, detalhe=None, ip=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO logs (usuario, acao, detalhe, ip) VALUES (?, ?, ?, ?)",
        (usuario, acao, detalhe, ip)
    )
    conn.commit()
    conn.close()