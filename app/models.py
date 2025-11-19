from app import db, bcrypt
from flask_login import UserMixin
from flask_security import RoleMixin 

# Flask Security trabalha com muitos para muitos entre usuários e roles
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin): 
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))
    

class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.String(255))

role_page_permission = db.Table('role_page_permission',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('page_id', db.Integer, db.ForeignKey('page.id'), primary_key=True)
)

Role.pages = db.relationship('Page', secondary=role_page_permission,
                            backref=db.backref('roles', lazy='dynamic'))

class User(db.Model, UserMixin): # <- Flask Login UserMixin
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
  
    password = db.Column(db.String(255), nullable=False)
    
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False) 
    
    
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    @property
    def role(self):
        if self.roles:
            return self.roles[0].name
        return None
