"""
tests/trathea_core/test_sanitizers.py
Testes dos sanitizadores de input do trathea_core.
"""
import pytest
from trathea_core.utils.sanitizers import sanitize_text, sanitize_html, sanitize_filename


class TestSanitizeText:
    """Testes do sanitize_text (remove tags perigosas, mantém texto seguro)."""

    def test_texto_limpo_sem_alteracao(self):
        texto = "Paciente relata dor de cabeça persistente."
        assert sanitize_text(texto) == texto

    def test_remove_tag_script(self):
        texto = '<script>alert("xss")</script>Texto seguro'
        result = sanitize_text(texto)
        assert "<script>" not in result
        assert "Texto seguro" in result

    def test_remove_tag_iframe(self):
        texto = '<iframe src="evil.com"></iframe>Conteúdo'
        result = sanitize_text(texto)
        assert "<iframe" not in result
        assert "Conteúdo" in result

    def test_remove_tag_style(self):
        texto = '<style>body{display:none}</style>Visível'
        result = sanitize_text(texto)
        assert "<style>" not in result

    def test_nao_string_retorna_original(self):
        assert sanitize_text(123) == 123
        assert sanitize_text(None) is None

    def test_remove_evento_inline(self):
        texto = '<div onmouseover="alert(1)">hover</div>'
        result = sanitize_text(texto)
        assert "onmouseover" not in result

    def test_strip_whitespace(self):
        assert sanitize_text("  texto com espaços  ") == "texto com espaços"


class TestSanitizeHtml:
    """Testes do sanitize_html (escapa todo HTML)."""

    def test_escapa_tags(self):
        result = sanitize_html("<b>bold</b>")
        assert "&lt;b&gt;" in result
        assert "<b>" not in result

    def test_escapa_aspas(self):
        result = sanitize_html('valor="teste"')
        assert "&quot;" in result

    def test_texto_simples_sem_alteracao(self):
        assert sanitize_html("Maria Santos") == "Maria Santos"

    def test_strip_whitespace(self):
        assert sanitize_html("  nome  ") == "nome"

    def test_nao_string_retorna_original(self):
        assert sanitize_html(42) == 42


class TestSanitizeFilename:
    """Testes do sanitize_filename."""

    def test_nome_valido_sem_alteracao(self):
        assert sanitize_filename("receita_001.pdf") == "receita_001.pdf"

    def test_remove_caracteres_especiais(self):
        result = sanitize_filename("arquivo@#$%!.pdf")
        assert "@" not in result
        assert "#" not in result

    def test_substitui_espacos_por_underscore(self):
        result = sanitize_filename("meu arquivo.pdf")
        assert " " not in result
        assert "_" in result

    def test_limita_comprimento(self):
        nome_longo = "a" * 300 + ".pdf"
        result = sanitize_filename(nome_longo)
        assert len(result) <= 255

    def test_nao_string_retorna_original(self):
        assert sanitize_filename(None) is None
