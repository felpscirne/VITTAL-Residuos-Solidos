from flask_security.forms import ConfirmRegisterForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, EqualTo

class ExtendedRegisterForm(ConfirmRegisterForm):
    name = StringField('Nome Completo', [DataRequired()])
    management_code = StringField('Código de Gestão (Opcional)')

    password_confirm = PasswordField('Confirmar Senha', [
        DataRequired(),
        EqualTo('password', message='As senhas devem ser iguais')
    ])