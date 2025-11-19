from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_security import Security

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
security = Security()