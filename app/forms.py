from flask_security.forms import RegisterForm
from wtforms import StringField
from wtforms.validators import DataRequired

class ExtendedRegisterForm(RegisterForm):
    name = StringField('Nome Completo', [DataRequired()])
    management_code = StringField('Código de Gestão (Opcional)')