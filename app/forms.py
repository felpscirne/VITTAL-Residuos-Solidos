import os

from flask_security.forms import ConfirmRegisterForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo


INSTITUTIONAL_EMAIL_SUFFIXES = (".edu", ".edu.br", ".ifrs.edu.br")


class ExtendedRegisterForm(ConfirmRegisterForm):
    name = StringField("Nome Completo", [DataRequired()])
    management_code = StringField("Codigo de Gestao (Opcional)")
    operator_code = StringField("Codigo de Operador (Opcional)")

    password_confirm = PasswordField(
        "Confirmar Senha",
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
        management_code = (self.management_code.data or "").strip()
        operator_code = (self.operator_code.data or "").strip()
        management_secret_code = os.getenv("MANAGEMENT_SECRET_CODE", "").strip()
        operator_secret_code = os.getenv("OPERATOR_SECRET_CODE", "").strip()

        has_institutional_email = email.endswith(INSTITUTIONAL_EMAIL_SUFFIXES)
        has_valid_management_code = bool(
            management_code
            and management_secret_code
            and management_code == management_secret_code
        )
        has_valid_operator_code = bool(
            operator_code
            and operator_secret_code
            and operator_code == operator_secret_code
        )
        has_valid_access_code = has_valid_management_code or has_valid_operator_code

        if management_code and not has_valid_management_code:
            self.management_code.errors.append("Codigo de gestao invalido.")
            return False

        if operator_code and not has_valid_operator_code:
            self.operator_code.errors.append("Codigo de operador invalido.")
            return False

        if not has_institutional_email and not has_valid_access_code:
            message = "Informe um e-mail institucional ou um codigo valido de gestao ou operador."
            self.email.errors.append(message)
            return False

        return True
