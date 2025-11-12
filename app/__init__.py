import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' 
login_manager.login_message = "Você precisa estar logado para acessar esta página."
login_manager.login_message_category = "info" 

def create_app():
    
    server = Flask(__name__, instance_relative_config=False)
    
    server.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    server.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(server)
    bcrypt.init_app(server)
    login_manager.init_app(server)

    with server.app_context():

        from . import models 

        @login_manager.user_loader
        def load_user(user_id):
            return models.User.query.get(int(user_id))


        from .routes import auth_routes
        server.register_blueprint(auth_routes.auth_bp)
        
        from .dash_app import create_dash_app
        app = create_dash_app(server)

        db.create_all()

        return server