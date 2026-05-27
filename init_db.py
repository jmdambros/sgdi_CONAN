import sqlite3

def init_db():
    conn = sqlite3.connect('demandas.db')
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prioridades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peso INTEGER,
        valor TEXT
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS demandas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        descricao TEXT,
        solicitante TEXT,
        data_criacao TEXT,
        prazo TEXT,
        status TEXT DEFAULT 'Aberta',
        id_prioridade INTEGER,
        FOREIGN KEY (id_prioridade) REFERENCES prioridades(id)
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comentarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        demanda_id INTEGER,
        comentario TEXT,
        autor TEXT,
        data TEXT,
        FOREIGN KEY (demanda_id) REFERENCES demandas(id)
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        criado_em TEXT DEFAULT (strftime('%d/%m/%Y %H:%M', 'now', 'localtime'))
    );
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM prioridades")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO prioridades (peso, valor) VALUES (1, 'Baixa'), (2, 'Média'), (3, 'Alta')")
        print("Prioridades configuradas.")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        acao TEXT NOT NULL,
        detalhe TEXT,
        ip TEXT,
        data TEXT DEFAULT (strftime('%d/%m/%Y %H:%M', 'now', 'localtime'))
    );
    ''')
    conn.commit()
    conn.close()
    print("Banco de dados pronto!")

if __name__ == '__main__':
    init_db()