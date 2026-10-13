
from django.core.exceptions import ValidationError


ALLOWED_EMAIL_DOMAINS = {"unifip.edu.br", "gmail.com"}


def validate_institutional_email(email: str) -> None:
    domain = email.rsplit("@", 1)[-1].lower()

    if domain not in ALLOWED_EMAIL_DOMAINS:
        raise ValidationError(
            "Utilize um e-mail institucional válido.",
            code="invalid_email_domain",
        )
