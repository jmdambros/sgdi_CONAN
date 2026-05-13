from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
from datetime import datetime, date
from functools import wraps
from auth import auth
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import io

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
        prazo = request.form['prazo'] or None

        solicitante = session['user_nome']

        conn = get_db()
        conn.execute(
            "INSERT INTO demandas (titulo, descricao, solicitante, data_criacao, id_prioridade, prazo) VALUES (?, ?, ?, ?, ?, ?)",
            (titulo, descricao, solicitante, datetime.now().strftime("%d/%m/%Y %H:%M"), id_prio, prazo)
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
    autor = session['user_nome']
    conn.execute(
        "INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (?, ?, ?, ?)",
        (demanda_id, request.form['comentario'], autor, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()
    return redirect(f'/detalhes/{demanda_id}')


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()

    total = conn.execute('SELECT COUNT(*) FROM demandas').fetchone()[0]
    abertas = conn.execute("SELECT COUNT(*) FROM demandas WHERE status = 'Aberta'").fetchone()[0]
    concluidas = conn.execute("SELECT COUNT(*) FROM demandas WHERE status = 'Concluída'").fetchone()[0]

    criticas = conn.execute("""
        SELECT d.*, p.valor as prioridade_nome 
        FROM demandas d
        LEFT JOIN prioridades p ON d.id_prioridade = p.id
        WHERE p.valor = 'Alta' AND d.status = 'Aberta'
        ORDER BY d.data_criacao ASC
    """).fetchall()

    atrasadas_count = conn.execute("""
        SELECT COUNT(*) FROM demandas 
        WHERE status = 'Aberta' AND prazo IS NOT NULL AND prazo < date('now')
    """).fetchone()[0]

    atrasadas_list = conn.execute("""
        SELECT d.*, p.valor as prioridade_nome 
        FROM demandas d
        LEFT JOIN prioridades p ON d.id_prioridade = p.id
        WHERE d.status = 'Aberta' AND d.prazo IS NOT NULL AND d.prazo < date('now')
        ORDER BY d.prazo ASC
    """).fetchall()

    por_responsavel = conn.execute("""
        SELECT solicitante, COUNT(*) as total
        FROM demandas
        WHERE status = 'Aberta'
        GROUP BY solicitante
        ORDER BY total DESC
    """).fetchall()

    tempo_medio = conn.execute("""
        SELECT AVG(
            julianday(substr(data_criacao,7,4)||'-'||substr(data_criacao,4,2)||'-'||substr(data_criacao,1,2)) -
            julianday(substr(data_criacao,7,4)||'-'||substr(data_criacao,4,2)||'-'||substr(data_criacao,1,2))
        ) FROM demandas WHERE status = 'Concluída'
    """).fetchone()[0]

    conn.close()

    pct_abertas = round((abertas / total * 100), 1) if total else 0
    pct_concluidas = round((concluidas / total * 100), 1) if total else 0
    pct_atrasadas = round((atrasadas_count / total * 100), 1) if total else 0

    return render_template('dashboard.html',
        total=total,
        abertas=abertas,
        concluidas=concluidas,
        atrasadas=atrasadas_count,
        atrasadas_list=atrasadas_list,
        criticas=criticas,
        por_responsavel=por_responsavel,
        tempo_medio=round(tempo_medio, 1) if tempo_medio else 0,
        pct_abertas=pct_abertas,
        pct_concluidas=pct_concluidas,
        pct_atrasadas=pct_atrasadas,
    )


@app.route('/exportar/atrasadas')
@login_required
def exportar_atrasadas():
    conn = get_db()
    atrasadas = conn.execute("""
        SELECT d.titulo, d.solicitante, d.prazo, d.data_criacao, p.valor as prioridade
        FROM demandas d
        LEFT JOIN prioridades p ON d.id_prioridade = p.id
        WHERE d.status = 'Aberta' AND d.prazo IS NOT NULL AND d.prazo < date('now')
        ORDER BY d.prazo ASC
    """).fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Demandas Atrasadas"

    ws.merge_cells('A1:E1')
    ws['A1'] = f"Relatório de Demandas Atrasadas — {date.today().strftime('%d/%m/%Y')}"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')

    headers = ['Título', 'Solicitante', 'Prazo', 'Data de Criação', 'Prioridade']
    header_fill = PatternFill(start_color='333333', end_color='333333', fill_type='solid')
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    red_fill = PatternFill(start_color='FCEBEB', end_color='FCEBEB', fill_type='solid')
    for row_idx, d in enumerate(atrasadas, 4):
        ws.cell(row=row_idx, column=1, value=d['titulo'])
        ws.cell(row=row_idx, column=2, value=d['solicitante'])
        ws.cell(row=row_idx, column=3, value=d['prazo'])
        ws.cell(row=row_idx, column=4, value=d['data_criacao'])
        ws.cell(row=row_idx, column=5, value=d['prioridade'])
        for col in range(1, 6):
            ws.cell(row=row_idx, column=col).fill = red_fill

    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 15

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"atrasadas_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
