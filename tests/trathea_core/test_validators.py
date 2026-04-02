"""
tests/trathea_core/test_validators.py
Testes dos validadores utilitários do trathea_core.
"""
import pytest
from trathea_core.utils.validators import validate_cpf, validate_cnpj, validate_crm


class TestCPFValidation:
    def test_cpf_valido(self):
        assert validate_cpf("98765432100") is True
        assert validate_cpf("987.654.321-00") is True

    def test_cpf_invalido_todos_iguais(self):
        assert validate_cpf("11111111111") is False

    def test_cpf_invalido_digito_verificador(self):
        assert validate_cpf("12345678900") is False  # dígito errado

    def test_cpf_comprimento_errado(self):
        assert validate_cpf("123") is False


class TestHashUtils:
    def test_hash_conteudo_deterministico(self):
        from trathea_core.signature.hash_utils import gerar_hash_conteudo

        dados = {"nome": "João", "cpf": "12345678909", "medicamento": "Dipirona"}
        hash1 = gerar_hash_conteudo(dados)
        hash2 = gerar_hash_conteudo(dados)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 = 64 hex chars

    def test_hash_diferente_para_dados_diferentes(self):
        from trathea_core.signature.hash_utils import gerar_hash_conteudo

        dados1 = {"nome": "João"}
        dados2 = {"nome": "Maria"}

        assert gerar_hash_conteudo(dados1) != gerar_hash_conteudo(dados2)

    def test_hash_verificacao_tem_64_chars(self):
        from trathea_core.signature.hash_utils import gerar_hash_verificacao

        token = gerar_hash_verificacao()
        assert len(token) == 64

    def test_hashes_verificacao_sao_unicos(self):
        from trathea_core.signature.hash_utils import gerar_hash_verificacao

        tokens = {gerar_hash_verificacao() for _ in range(100)}
        assert len(tokens) == 100  # todos únicos
