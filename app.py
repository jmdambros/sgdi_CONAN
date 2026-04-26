from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
from functools import wraps
from auth import auth

app = Flask(__name__)
app.secret_key = 'dalessandro2010'

app.register_blueprint(auth)


def get_db():
    conn = sqlite3.connect('demandas.db')
    conn.row_factory = sqlite3.Row
    return conn


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para continuar.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
@login_required
def index():
    conn = get_db()
    query = '''
        SELECT d.*, p.valor as prioridade_nome 
        FROM demandas d 
        LEFT JOIN prioridades p ON d.id_prioridade = p.id
        ORDER BY p.peso DESC, d.data_criacao ASC
        LIMIT 10
    '''
    demandas = conn.execute(query).fetchall()
    total = conn.execute('SELECT COUNT(*) FROM demandas').fetchone()[0]
    conn.close()
    return render_template('index.html', demandas=demandas, total=total, offset=10)


@app.route('/mais_demandas')
@login_required
def mais_demandas():
    offset = int(request.args.get('offset', 10))
    conn = get_db()
    query = '''
        SELECT d.*, p.valor as prioridade_nome 
        FROM demandas d 
        LEFT JOIN prioridades p ON d.id_prioridade = p.id
        ORDER BY p.peso DESC, d.data_criacao ASC
        LIMIT 10 OFFSET ?
    '''
    demandas = conn.execute(query, (offset,)).fetchall()
    conn.close()
    return render_template('linhas_demandas.html', demandas=demandas)


@app.route('/nova_demanda', methods=['GET', 'POST'])
@login_required
def nova_demanda():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        id_prio = request.form['id_prioridade']

        solicitante = session['user_nome']

        conn = get_db()
        conn.execute(
            "INSERT INTO demandas (titulo, descricao, solicitante, data_criacao, id_prioridade) VALUES (?, ?, ?, ?, ?)",
            (titulo, descricao, solicitante, datetime.now().strftime("%d/%m/%Y %H:%M"), id_prio)
        )
        conn.commit()
        conn.close()
        flash('Demanda criada!', 'success')
        return redirect('/')
    
    conn = get_db()
    prioridades = conn.execute('SELECT * FROM prioridades ORDER BY peso DESC').fetchall()
    conn.close()
    return render_template('nova_demanda.html', prioridades=prioridades)


@app.route('/deletar/<id>')
@login_required
def deletar(id):
    conn = get_db()
    conn.execute('DELETE FROM demandas WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')


@app.route('/buscar')
@login_required
def buscar():
    termo = request.args.get('q', '').strip()
    conn = get_db()
    query = '''
        SELECT d.*, p.valor as prioridade_nome 
        FROM demandas d 
        LEFT JOIN prioridades p ON d.id_prioridade = p.id 
        WHERE d.titulo LIKE ? OR p.valor LIKE ?
        ORDER BY p.peso DESC, d.id ASC
    '''
    filtro = f'%{termo}%'
    resultados = conn.execute(query, (filtro, filtro)).fetchall()
    conn.close()
    total = len(resultados)
    return render_template('index.html', demandas=resultados, total=total, offset=total)

@app.route('/detalhes/<id>')
@login_required
def detalhes(id):
    conn = get_db()
    demanda = conn.execute('''
        SELECT d.*, p.valor as prioridade_nome 
        FROM demandas d 
        LEFT JOIN prioridades p ON d.id_prioridade = p.id 
        WHERE d.id=?''', (id,)).fetchone()
    comentarios = conn.execute('SELECT * FROM comentarios WHERE demanda_id=?', (id,)).fetchall()
    conn.close()
    return render_template('detalhes.html', demanda=demanda, comentarios=comentarios)


@app.route('/adicionar_comentario/<demanda_id>', methods=['POST'])
@login_required
def adicionar_comentario(demanda_id):
    conn = get_db()
    # Author is always the logged-in user
    autor = session['user_nome']
    conn.execute(
        "INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (?, ?, ?, ?)",
        (demanda_id, request.form['comentario'], autor, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()
    return redirect(f'/detalhes/{demanda_id}')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')