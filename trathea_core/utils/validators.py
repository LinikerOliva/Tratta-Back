"""
trathea_core/utils/validators.py
Validadores reutilizáveis: CPF, CNPJ, CRM.
"""
import re


def validate_cpf(cpf: str) -> bool:
    """
    Valida um CPF brasileiro.
    Aceita formatos: '12345678909' ou '123.456.789-09'
    """
    cpf = re.sub(r"\D", "", cpf)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    # Primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10

    # Segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10

    return int(cpf[9]) == digito1 and int(cpf[10]) == digito2


def validate_cnpj(cnpj: str) -> bool:
    """
    Valida um CNPJ brasileiro.
    Aceita formatos: '11222333000181' ou '11.222.333/0001-81'
    """
    cnpj = re.sub(r"\D", "", cnpj)

    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def calcular_digito(cnpj: str, pesos: list[int]) -> int:
        soma = sum(int(cnpj[i]) * pesos[i] for i in range(len(pesos)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    d1 = calcular_digito(cnpj, pesos1)
    d2 = calcular_digito(cnpj, pesos2)

    return int(cnpj[12]) == d1 and int(cnpj[13]) == d2


def validate_crm(crm: str) -> bool:
    """
    Valida formato básico de CRM: números com 4 a 6 dígitos.
    Formato aceito: '123456' ou 'CRM/SP 123456'
    """
    crm_numeros = re.sub(r"\D", "", crm)
    return 4 <= len(crm_numeros) <= 7


def format_cpf(cpf: str) -> str:
    """Formata CPF para o padrão XXX.XXX.XXX-XX."""
    cpf = re.sub(r"\D", "", cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf


def format_cnpj(cnpj: str) -> str:
    """Formata CNPJ para o padrão XX.XXX.XXX/XXXX-XX."""
    cnpj = re.sub(r"\D", "", cnpj)
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}" if len(cnpj) == 14 else cnpj
