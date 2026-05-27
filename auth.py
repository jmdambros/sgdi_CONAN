from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
import hashlib
import os
from logger import log_action

auth = Blueprint('auth', __name__)

def get_db():
    conn = sqlite3.connect('demandas.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hashed, salt


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm = request.form['confirm_password']

        if not nome or not email or not password:
            flash('Preencha todos os campos.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('register.html')

        conn = get_db()
        existing = conn.execute('SELECT id FROM usuarios WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Este e-mail já está cadastrado.', 'danger')
            conn.close()
            return render_template('register.html')

        hashed, salt = hash_password(password)
        conn.execute(
            'INSERT INTO usuarios (nome, email, senha_hash, salt) VALUES (?, ?, ?, ?)',
            (nome, email, hashed, salt)
        )
        conn.commit()
        conn.close()

        log_action('sistema', 'REGISTRO', f'Novo usuário: {nome} ({email})', request.remote_addr)

        flash('Conta criada com sucesso! Faça login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        conn = get_db()
        user = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
        conn.close()

        if not user:
            log_action('desconhecido', 'LOGIN_FALHOU', f'Tentativa com e-mail: {email}', request.remote_addr)
            flash('E-mail ou senha inválidos.', 'danger')
            return render_template('login.html')

        hashed, _ = hash_password(password, user['salt'])
        if hashed != user['senha_hash']:
            log_action(user['nome'], 'LOGIN_FALHOU', f'Senha incorreta para: {email}', request.remote_addr)
            flash('E-mail ou senha inválidos.', 'danger')
            return render_template('login.html')

        session['user_id'] = user['id']
        session['user_nome'] = user['nome']
        session['user_email'] = user['email']

        log_action(user['nome'], 'LOGIN', f'Usuário: {email}', request.remote_addr)

        flash(f'Bem-vindo, {user["nome"]}!', 'success')
        return redirect(url_for('index'))

    return render_template('login.html')


@auth.route('/logout')
def logout():
    log_action(
        session.get('user_nome', 'desconhecido'),
        'LOGOUT',
        f'Usuário: {session.get("user_email")}',
        request.remote_addr
    )
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('auth.login'))