"""
trathea_core/pdf/pdf_generator.py
Geração de PDFs para receitas e prontuários.

NOTA: WeasyPrint foi removido por incompatibilidade com Windows (requer GTK).
Em produção, substitua por ReportLab, xhtml2pdf ou outro gerador compatível.
"""
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger("trathea")

# Diretório dos templates HTML para PDF
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _pdf_placeholder(titulo: str, dados: dict) -> bytes:
    """
    Gera um PDF minimalista em texto puro (sem dependências externas).
    Adequado para desenvolvimento local. Em produção, instale ReportLab ou xhtml2pdf.
    """
    conteudo = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj

4 0 obj
<< /Length 200 >>
stream
BT
/F1 16 Tf
50 750 Td
({titulo}) Tj
/F1 10 Tf
0 -30 Td
(Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}) Tj
0 -20 Td
(ID: {dados.get('id', 'N/A')}) Tj
ET
endstream
endobj

5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj

xref
0 6

trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF"""
    return conteudo.encode("latin-1", errors="replace")


def gerar_pdf_receita(receita_data: dict) -> bytes:
    """
    Gera o PDF de uma receita médica a partir dos dados serializados.

    Args:
        receita_data: Dicionário com todos os dados da receita
                      (médico, paciente, itens, assinatura, etc.)

    Returns:
        Bytes do PDF gerado.

    Raises:
        PDFGenerationError: Se falhar na geração.
    """
    try:
        # Tenta usar xhtml2pdf se disponível (leve, funciona no Windows)
        try:
            from xhtml2pdf import pisa

            html_content = render_to_string(
                "pdf/receita.html",
                {"receita": receita_data, "static_root": settings.STATIC_ROOT},
            )
            buffer = io.BytesIO()
            result = pisa.CreatePDF(io.StringIO(html_content), dest=buffer)
            if not result.err:
                logger.info(f"PDF receita gerado (xhtml2pdf) — ID: {receita_data.get('id')}")
                return buffer.getvalue()
        except ImportError:
            pass  # xhtml2pdf não instalado — usa fallback

        # Fallback: PDF placeholder para desenvolvimento
        logger.warning(
            "Gerador de PDF não disponível (weasyprint/xhtml2pdf não instalados). "
            "Retornando PDF placeholder para desenvolvimento."
        )
        pdf_bytes = _pdf_placeholder("RECEITA MÉDICA - TRATHEA", receita_data)
        logger.info(f"PDF receita (placeholder) — ID: {receita_data.get('id')}")
        return pdf_bytes

    except Exception as e:
        logger.error(f"Erro ao gerar PDF receita: {e}", exc_info=True)
        raise PDFGenerationError(f"Falha ao gerar PDF: {str(e)}")


def gerar_pdf_prontuario(prontuario_data: dict) -> bytes:
    """
    Gera o PDF de um prontuário médico.

    Args:
        prontuario_data: Dados do prontuário.

    Returns:
        Bytes do PDF gerado.
    """
    try:
        try:
            from xhtml2pdf import pisa

            html_content = render_to_string(
                "pdf/prontuario.html",
                {"prontuario": prontuario_data},
            )
            buffer = io.BytesIO()
            result = pisa.CreatePDF(io.StringIO(html_content), dest=buffer)
            if not result.err:
                return buffer.getvalue()
        except ImportError:
            pass

        logger.warning("Gerador de PDF não disponível. Retornando placeholder.")
        return _pdf_placeholder("PRONTUÁRIO MÉDICO - TRATHEA", prontuario_data)

    except Exception as e:
        logger.error(f"Erro ao gerar PDF prontuário: {e}", exc_info=True)
        raise PDFGenerationError(f"Falha ao gerar PDF do prontuário: {str(e)}")


class PDFGenerationError(Exception):
    """Erro durante a geração de PDF."""
    pass
