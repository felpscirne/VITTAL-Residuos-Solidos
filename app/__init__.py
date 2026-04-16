import os

from dotenv import load_dotenv
from flask import Flask
from flask_security import SQLAlchemyUserDatastore, user_registered

from app.extensions import bcrypt, cache, db, mail, security
from app.models import Role, User
from app.services.rbac_bootstrap import run_startup_migrations

load_dotenv()


def create_app():
    server = Flask(__name__, instance_relative_config=False)

    server.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    server.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    server.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", 1800)),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT_SECONDS", 30)),
    }

    server.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
    server.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
    server.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True").lower() in ["true", "1"]
    server.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    server.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    server.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

    server.config["SECURITY_PASSWORD_SALT"] = os.getenv("SECURITY_PASSWORD_SALT")
    server.config["SECURITY_REGISTERABLE"] = True
    server.config["SECURITY_CONFIRMABLE"] = True
    server.config["SECURITY_RECOVERABLE"] = True
    server.config["SECURITY_CHANGEABLE"] = True
    server.config["SECURITY_EMAIL_SUBJECT_REGISTER"] = "Bem-vindo ao VITTAL Transbordo - IFEsCS"
    server.config["AUTO_MIGRATE_ON_STARTUP"] = os.getenv("AUTO_MIGRATE_ON_STARTUP", "True").lower() in ["true", "1"]

    server.config["SECURITY_POST_LOGIN_VIEW"] = "/"
    server.config["SECURITY_POST_LOGOUT_VIEW"] = "/"
    server.config["SECURITY_POST_REGISTER_VIEW"] = "/login"

    cache_dir = os.getenv("CACHE_DIR") or os.path.join(server.instance_path, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    server.config["CACHE_TYPE"] = os.getenv("CACHE_TYPE", "FileSystemCache")
    server.config["CACHE_DIR"] = cache_dir
    server.config["CACHE_DEFAULT_TIMEOUT"] = int(os.getenv("CACHE_DEFAULT_TIMEOUT", 3600))
    server.config["CACHE_THRESHOLD"] = int(os.getenv("CACHE_THRESHOLD", 500))

    from app.forms import ExtendedRegisterForm

    server.config["SECURITY_CONFIRM_REGISTER_FORM"] = ExtendedRegisterForm
    server.config["SECURITY_REGISTER_FORM"] = ExtendedRegisterForm

    db.init_app(server)
    bcrypt.init_app(server)
    mail.init_app(server)
    cache.init_app(server)

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(server, user_datastore)

    @user_registered.connect_via(server)
    def user_registered_sighandler(app, user, confirm_token, form_data, **kwargs):
        user.name = form_data.get("name")
        user.email = (user.email or "").strip().lower()

        access_code = (form_data.get("access_code") or "").strip()
        management_secret_code = os.getenv("MANAGEMENT_SECRET_CODE", "").strip()
        operator_secret_code = os.getenv("OPERATOR_SECRET_CODE", "").strip()

        role_name = "anonymous"

        if access_code and management_secret_code and access_code == management_secret_code:
            role_name = "management"
        elif access_code and operator_secret_code and access_code == operator_secret_code:
            role_name = "operator"
        elif user.email.endswith((".edu", ".edu.br", ".ifrs.edu.br")):
            role_name = "student"

        role_obj = user_datastore.find_role(role_name)
        if not role_obj:
            role_obj = user_datastore.find_role("anonymous")

        user.role_ref = role_obj
        db.session.commit()

    with server.app_context():
        if server.config["AUTO_MIGRATE_ON_STARTUP"]:
            run_startup_migrations()

        from .dash_app import create_dash_app

        create_dash_app(server)
        return server
