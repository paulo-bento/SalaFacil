
from django.core.exceptions import ValidationError


ALLOWED_EMAIL_DOMAINS = {
    "unifip.edu.br", # E-mail da UNIFIP
    "ads.fiponline.edu.br", # E-mail do curso de ADS da UNIFIP
    "gmail.com", # Apenas para testes
}


def validate_institutional_email(email: str) -> None:
    domain = email.rsplit("@", 1)[-1].lower()

    if domain not in ALLOWED_EMAIL_DOMAINS:
        raise ValidationError(
            "Utilize um e-mail institucional válido.",
            code="invalid_email_domain",
        )
