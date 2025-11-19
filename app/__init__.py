import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

# --- NOVOS IMPORTS ---
from flask_mail import Mail
from flask_security import Security, SQLAlchemyUserDatastore
from app.models import db, User, Role 

load_dotenv()


bcrypt = Bcrypt() 
mail = Mail() 
security = Security()


def create_app():
    
    server = Flask(__name__, instance_relative_config=False, template_folder='templates')
    

    server.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    server.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configuração de E-mail
    server.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    server.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    server.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1']
    server.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    server.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    server.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    # Configuração do Flask-Security
    server.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT')
    server.config['SECURITY_REGISTERABLE'] = True # HABILITA REGISTRO DE USUÁRIOS
    server.config['SECURITY_CONFIRMABLE'] = True # HABILITA CONFIRMAÇÃO DE E-MAIL
    server.config['SECURITY_RECOVERABLE'] = True # HABILITA RESET DE SENHA
    server.config['SECURITY_CHANGEABLE'] = True # Permite que usuários mudem a senha
    server.config['SECURITY_EMAIL_SUBJECT_REGISTER'] = "Bem-vindo ao Dashboard IFEsCS!"
    server.config['SECURITY_LOGIN_USER_TEMPLATE'] = 'security/login_user.html'
    server.config['SECURITY_REGISTER_USER_TEMPLATE'] = 'security/register_user.html'
    server.config['SECURITY_FORGOT_PASSWORD_TEMPLATE'] = 'security/forgot_password.html'
    server.config['SECURITY_RESET_PASSWORD_TEMPLATE'] = 'security/reset_password.html'
    
    
    db.init_app(server)
    bcrypt.init_app(server)
    mail.init_app(server)
    
    
    
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(server, user_datastore)

    with server.app_context():
        
        from . import models 
        
        from .routes import auth_routes
        server.register_blueprint(auth_routes.auth_bp)
        
        
        from .dash_app import create_dash_app
        app = create_dash_app(server)

        db.create_all()

        return server