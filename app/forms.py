import os

from flask_security.forms import ConfirmRegisterForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo


INSTITUTIONAL_EMAIL_SUFFIXES = (".edu", ".edu.br", ".ifrs.edu.br")


class ExtendedRegisterForm(ConfirmRegisterForm):
    name = StringField("Nome completo", [DataRequired()])
    access_code = StringField("Código de acesso (opcional)")

    password_confirm = PasswordField(
        "Confirmar senha",
        [
            DataRequired(),
            EqualTo("password", message="As senhas devem ser iguais"),
        ],
    )

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators=extra_validators)
        if not is_valid:
            return False

        email = (self.email.data or "").strip().lower()
        access_code = (self.access_code.data or "").strip()
        management_secret_code = os.getenv("MANAGEMENT_SECRET_CODE", "").strip()
        operator_secret_code = os.getenv("OPERATOR_SECRET_CODE", "").strip()

        has_institutional_email = email.endswith(INSTITUTIONAL_EMAIL_SUFFIXES)
        is_management_code = bool(
            access_code
            and management_secret_code
            and access_code == management_secret_code
        )
        is_operator_code = bool(
            access_code
            and operator_secret_code
            and access_code == operator_secret_code
        )
        has_valid_access_code = is_management_code or is_operator_code

        if access_code and not has_valid_access_code:
            self.access_code.errors.append("Código de acesso inválido.")
            return False

        if not has_institutional_email and not has_valid_access_code:
            message = "Informe um e-mail institucional ou um código de acesso válido."
            self.email.errors.append(message)
            return False

        return True
