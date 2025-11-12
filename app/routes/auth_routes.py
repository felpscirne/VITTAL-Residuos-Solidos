from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db, bcrypt
from app.models import User
import os

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('/')) 
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('/'))
        else:
            flash('Login falhou. Verifique o email e a senha.', 'danger')
            
    return render_template('login.html', title='Login')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('/'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        management_code = request.form.get('management_code')
        secret_code = os.getenv('MANAGEMENT_SECRET_CODE')

        role = 'geral' # Padrão
        
        if management_code and secret_code and management_code == secret_code:
            # Se o código bater, dá o acesso de Gestão
            role = 'gestao'
            flash('Código de gestão correto! Conta de Gestor criada.', 'success')
            
        elif email.endswith(('.edu', '.edu.br', '.ifrs.edu.br')):
            # Se não for gestor, verifica se é estudante
            role = 'estudantil'
            flash('Email institucional detectado. Conta de Estudante criada.', 'info')
        else:
            # Senão, é usuário geral
            flash('Conta de Acesso Geral criada.', 'info')
        user = User(email=email, name=name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Conta criada com sucesso! Você já pode fazer login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html', title='Registro')