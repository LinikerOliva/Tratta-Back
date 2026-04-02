"""
trathea_core/signature/hash_utils.py
Utilitários de geração e verificação de hash para documentos.
"""
import hashlib
import json
import secrets
import string
from typing import Any


def gerar_hash_conteudo(dados: dict) -> str:
    """
    Gera um hash SHA-256 do conteúdo serializado de forma canônica.
    Garante o mesmo hash independente da ordem das chaves.

    Args:
        dados: Dicionário com os dados do documento.

    Returns:
        Hash SHA-256 em hexadecimal.
    """
    conteudo_canonical = json.dumps(dados, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(conteudo_canonical.encode("utf-8")).hexdigest()


def gerar_hash_pdf(pdf_bytes: bytes) -> str:
    """
    Gera um hash SHA-256 dos bytes de um PDF.

    Args:
        pdf_bytes: Conteúdo binário do PDF.

    Returns:
        Hash SHA-256 em hexadecimal.
    """
    return hashlib.sha256(pdf_bytes).hexdigest()


def gerar_hash_verificacao() -> str:
    """
    Gera um token público único para verificação de receitas (QR Code).
    Usa 32 bytes de aleatoriedade = 64 caracteres hex.

    Returns:
        Token hexadecimal de 64 caracteres.
    """
    return secrets.token_hex(32)


def verificar_hash(dados: dict, hash_esperado: str) -> bool:
    """
    Verifica se o hash de um conjunto de dados bate com o esperado.

    Args:
        dados: Dados originais do documento.
        hash_esperado: Hash armazenado no banco.

    Returns:
        True se o hash for válido.
    """
    hash_calculado = gerar_hash_conteudo(dados)
    return secrets.compare_digest(hash_calculado, hash_esperado)
