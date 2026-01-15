from app.extensions import db
from flask_security import RoleMixin, UserMixin

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

class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False) # Ex: "Manutenção Balança 01"
    description = db.Column(db.Text)                  # Detalhes
    event_type = db.Column(db.String(50))             # Ex: "Manutenção", "Feriado", "Greve"
    
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # Setores afetados
    affected_sectors = db.Column(db.String(255)) 
    
    created_at = db.Column(db.DateTime, default=db.func.now())