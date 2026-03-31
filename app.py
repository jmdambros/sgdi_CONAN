from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = '123456'

def get_db():
    conn = sqlite3.connect('demandas.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db()
    query = '''
        SELECT d.*, p.valor as prioridade_nome 
        FROM demandas d 
        LEFT JOIN prioridades p ON d.id_prioridade = p.id
        ORDER BY p.peso DESC, d.id ASC
    '''
    demandas = conn.execute(query).fetchall()
    conn.close()
    return render_template('index.html', demandas=demandas)

@app.route('/nova_demanda', methods=['GET', 'POST'])
def nova_demanda():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        solicitante = request.form['solicitante']
        id_prio = request.form['id_prioridade']
        
        conn = get_db()
        conn.execute(
            "INSERT INTO demandas (titulo, descricao, solicitante, data_criacao, id_prioridade) VALUES (?, ?, ?, ?, ?)",
            (titulo, descricao, solicitante, datetime.now().strftime("%d/%m/%Y %H:%M"), id_prio)
        )
        conn.commit()
        conn.close()
        flash('Demanda criada!')
        return redirect('/')
    return render_template('nova_demanda.html')

@app.route('/editar/<id>', methods=['GET', 'POST'])
def editar(id):
    conn = get_db()
    if request.method == 'POST':
        conn.execute(
            "UPDATE demandas SET titulo=?, descricao=?, solicitante=? WHERE id=?",
            (request.form['titulo'], request.form['descricao'], request.form['solicitante'], id)
        )
        conn.commit()
        conn.close()
        flash('Alterações salvas (Prioridade mantida conforme original).')
        return redirect('/')
    demanda = conn.execute('''
        SELECT d.*, p.valor as prioridade_nome 
        FROM demandas d 
        LEFT JOIN prioridades p ON d.id_prioridade = p.id 
        WHERE d.id=?''', (id,)).fetchone()
    conn.close()
    return render_template('editar.html', demanda=demanda)

@app.route('/deletar/<id>')
def deletar(id):
    conn = get_db()
    conn.execute('DELETE FROM demandas WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/buscar')
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
    return render_template('index.html', demandas=resultados)

@app.route('/detalhes/<id>')
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
def adicionar_comentario(demanda_id):
    conn = get_db()
    conn.execute(
        "INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (?, ?, ?, ?)",
        (demanda_id, request.form['comentario'], request.form['autor'], datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()
    return redirect(f'/detalhes/{demanda_id}')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')