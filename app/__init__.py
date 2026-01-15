import os
from flask import Flask
from dotenv import load_dotenv
from flask_security import SQLAlchemyUserDatastore, user_registered
from app.extensions import db, bcrypt, mail, security, cache
from app.models import db, User, Role

load_dotenv()

def create_app():
    server = Flask(__name__, instance_relative_config=False)
    
    # --- Configs ---
    server.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    server.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configs de Email
    server.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    server.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    server.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1']
    server.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    server.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    server.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    # Configs do Flask-Security
    server.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT')
    server.config['SECURITY_REGISTERABLE'] = True
    server.config['SECURITY_CONFIRMABLE'] = True
    server.config['SECURITY_RECOVERABLE'] = True
    server.config['SECURITY_CHANGEABLE'] = True
    server.config['SECURITY_EMAIL_SUBJECT_REGISTER'] = "Bem-vindo ao Dashboard IFEsCS!"
    
    server.config['SECURITY_POST_LOGIN_VIEW'] = '/'
    server.config['SECURITY_POST_LOGOUT_VIEW'] = '/'
    server.config['SECURITY_POST_REGISTER_VIEW'] = '/login'

    from app.forms import ExtendedRegisterForm
    server.config['SECURITY_CONFIRM_REGISTER_FORM'] = ExtendedRegisterForm
    server.config['SECURITY_REGISTER_FORM'] = ExtendedRegisterForm

    
    db.init_app(server)
    bcrypt.init_app(server)
    mail.init_app(server)
    cache.init_app(server)

    
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(server, user_datastore)

    
    @user_registered.connect_via(server)
    def user_registered_sighandler(app, user, confirm_token, form_data, **kwargs):
        
        user.name = form_data.get('name')
        
        
        management_code = form_data.get('management_code')
        secret_code = os.getenv('MANAGEMENT_SECRET_CODE')
        
        role_name = 'geral'
        
        if management_code and secret_code and management_code == secret_code:
            role_name = 'gestao'
        elif user.email.endswith(('.edu', '.edu.br', '.ifrs.edu.br')):
            role_name = 'estudantil'
            
        role_obj = user_datastore.find_role(role_name)
        if not role_obj:
             role_obj = user_datastore.find_role('geral')
        
        user_datastore.add_role_to_user(user, role_obj)
        db.session.commit()

    with server.app_context():
        
        
        from .dash_app import create_dash_app
        app = create_dash_app(server)

        db.create_all()
        return server