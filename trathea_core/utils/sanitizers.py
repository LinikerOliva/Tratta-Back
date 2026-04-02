"""
trathea_core/utils/sanitizers.py
Sanitização de inputs para prevenir XSS.
"""
import re
import html


# Tags HTML completamente perigosas
DANGEROUS_TAGS = re.compile(
    r"<(script|style|iframe|object|embed|link|meta|base|form|input|button)[^>]*>.*?</\1>|"
    r"<(script|style|iframe|object|embed|link|meta|base|form|input|button)[^>]*/?>",
    re.IGNORECASE | re.DOTALL,
)

# Atributos perigosos (eventos JS inline)
DANGEROUS_ATTRS = re.compile(
    r'\s*(on\w+|javascript:|data:)\s*=\s*["\'][^"\']*["\']',
    re.IGNORECASE,
)


def sanitize_text(value: str) -> str:
    """
    Remove tags HTML perigosas e escapa caracteres especiais.
    Use em campos de texto livre (ex: anamnese, observações).
    """
    if not isinstance(value, str):
        return value
    value = DANGEROUS_TAGS.sub("", value)
    value = DANGEROUS_ATTRS.sub("", value)
    return value.strip()


def sanitize_html(value: str) -> str:
    """
    Escapa COMPLETAMENTE o HTML (para campos onde HTML não é permitido).
    Use em nomes, CPFs, emails, etc.
    """
    if not isinstance(value, str):
        return value
    return html.escape(value.strip())


def sanitize_filename(filename: str) -> str:
    """Remove caracteres perigosos de nomes de arquivo."""
    if not isinstance(filename, str):
        return filename
    filename = re.sub(r"[^\w\s\-\.]", "", filename)
    filename = re.sub(r"\s+", "_", filename)
    return filename[:255]
