from app.extensions import db
from flask_security import RoleMixin, UserMixin


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.String(255))


role_page_permission = db.Table(
    'role_page_permission',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('page_id', db.Integer, db.ForeignKey('page.id'), primary_key=True),
)

Role.pages = db.relationship(
    'Page',
    secondary=role_page_permission,
    backref=db.backref('roles', lazy='dynamic'),
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    role_id = db.Column(db.Integer(), db.ForeignKey('role.id'))
    role_ref = db.relationship('Role', foreign_keys=[role_id], backref=db.backref('users', lazy='dynamic'))
    roles = db.relationship(
        'Role',
        primaryjoin='User.role_id == Role.id',
        foreign_keys=[role_id],
        uselist=True,
        viewonly=True,
    )

    @property
    def role(self):
        if self.role_ref:
            return self.role_ref.name
        return None


class Event(db.Model):
    __tablename__ = 'event'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50))
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    affected_sectors = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
