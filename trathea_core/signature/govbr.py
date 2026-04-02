"""
trathea_core/signature/govbr.py
Integração com API de Assinatura Avançada do GOV.BR e ICP-Brasil (ITI).
"""
import os
import secrets
import json
import base64
from authlib.integrations.requests_client import OAuth2Session
from django.core.cache import cache

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import qrcode
from io import BytesIO

# Configurações do GOV.BR (normalmente viriam do .env)
CLIENT_ID = os.environ.get("GOVBR_CLIENT_ID", "govbr_test_client_id")
CLIENT_SECRET = os.environ.get("GOVBR_CLIENT_SECRET", "govbr_test_secret")
REDIRECT_URI = os.environ.get("GOVBR_REDIRECT_URI", "http://localhost:3000/medico/assinatura/callback")

AUTHORIZATION_URL = "https://cas.acesso.gov.br/oauth2/authorize"
TOKEN_URL = "https://cas.acesso.gov.br/oauth2/token"
ITI_SIGNATURE_API = "https://assinatura.iti.gov.br/api/v2/assinador"

class GovBrSignatureIntegration:
    """Implementa o fluxo de assinatura digital com GOV.BR/ITI."""

    @staticmethod
    def gerar_pdf_receita_bruto(medico, paciente, medicamentos, observacoes) -> bytes:
        """Gera um PDF bruto e real da receita usando ReportLab."""
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        # Cabeçalho
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 750, f"Receituário - Dr(a). {medico.user.nome_completo}")
        p.setFont("Helvetica", 12)
        p.drawString(100, 730, f"CRM: {medico.crm} - {medico.crm_estado}")
        
        # Dados do Paciente
        p.line(100, 715, 500, 715)
        p.drawString(100, 690, f"Paciente: {paciente.user.nome_completo}")
        p.drawString(100, 670, f"CPF: {paciente.user.cpf}")

        # Medicamentos
        y = 630
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "PRESCRIÇÃO:")
        y -= 30
        p.setFont("Helvetica", 12)
        
        for i, item in enumerate(medicamentos):
            # Formato: 1. Nome - Dosagem
            p.drawString(100, y, f"{i+1}. {item.get('nome')} - {item.get('dosagem', 'N/A')}")
            y -= 20
            # Uso e Posologia
            uso_via = f"Uso: {item.get('via', 'Oral')} | {item.get('posologia', '')} | Qtd: {item.get('quantidade', '')}"
            p.drawString(120, y, uso_via)
            y -= 30
            if y < 100:
                p.showPage()
                y = 750

        # Observações
        if observacoes:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y, "Observações e Recomendações:")
            y -= 20
            p.setFont("Helvetica", 11)
            # Divisão básica de linhas
            for linha in str(observacoes).split('\n'):
                p.drawString(100, y, linha.strip())
                y -= 15

        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def iniciar_fluxo_govbr(hash_documento: str, consulta_id: int):
        """
        Inicia o OAuth2 com Gov.br, salva o state no Redis (cache),
        e retorna a URL para redirecionar o médico.
        """
        state = secrets.token_urlsafe(32)
        cache.set(f"govbr_state_{state}", {"hash": hash_documento, "consulta_id": consulta_id}, timeout=900)
        
        # Na integração real do ITI via OAuth2, o escopo costuma ser `signature` ou base `openid`
        client = OAuth2Session(CLIENT_ID, CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope="openid assinatura")
        url, _ = client.create_authorization_url(AUTHORIZATION_URL, state=state)
        
        return url

    @staticmethod
    def processar_callback(code: str, state: str):
        """
        Recebe o code OAuth2, troca por token, e usa a API do ITI para assinar.
        Retorna o UUID do artefato assinado (ou mock para o ambiente).
        """
        session_data = cache.get(f"govbr_state_{state}")
        if not session_data:
            raise ValueError("Sessão expirada ou inválida.")
            
        hash_doc = session_data["hash"]
        consulta_id = session_data["consulta_id"]
        
        # ── FLUXO REAL: client.fetch_token() ──────
        # client = OAuth2Session(CLIENT_ID, CLIENT_SECRET, redirect_uri=REDIRECT_URI)
        # token = client.fetch_token(TOKEN_URL, code=code)
        
        # ── FLUXO ITI ASINATURA ──────────────────
        # headers = {"Authorization": f"Bearer {token['access_token']}"}
        # payload = {"hashes": [hash_doc]}
        # resp = requests.post(f"{ITI_SIGNATURE_API}/assinar", json=payload, headers=headers)
        # assinaturas = resp.json()["assinaturas"] # PKS#7 ou CAdES
        
        # MOCK para simular resposta de sucesso do ITI:
        artefato_assinatura = f"assinado_govbr_mock_pks7_{hash_doc[:8]}"
        
        return {
            "consulta_id": consulta_id,
            "hash_original": hash_doc,
            "artefato": artefato_assinatura,
            "verification_url": f"https://assinatura.iti.gov.br/validar/?hash={hash_doc[:8]}"
        }

    @staticmethod
    def carimbar_pdf(pdf_original_bytes: bytes, verification_url: str) -> bytes:
        """
        Adiciona o QR Code de Validação do ICP-Brasil (ITI) no final do documento, 
        carimbando visualmente (e criptograficamente num caso real PDE/CAdES).
        """
        import sys
        from PyPDF2 import PdfWriter, PdfReader

        # 1. Gerar imagem do QR Code
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(verification_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Salva o QR temporariamente na memória
        qr_buffer = BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        # 2. Criar uma nova página de "Carimbo" com o QRCode usando ReportLab
        carimbo_buffer = BytesIO()
        p = canvas.Canvas(carimbo_buffer, pagesize=A4)
        
        # Desenhamos o carimbo de ICP-Brasil / Gov.Br no canto inferior esquerdo/direito.
        # Por simplicidade, colocamos numa posição fixa inferior (y=100)
        from reportlab.lib.utils import ImageReader
        logo_qr = ImageReader(qr_buffer)
        p.drawImage(logo_qr, 100, 50, width=80, height=80)
        
        p.setFont("Helvetica-Bold", 10)
        p.drawString(190, 110, "Documento assinado digitalmente com GOV.BR (Padrão ICP-Brasil).")
        p.setFont("Helvetica", 9)
        p.drawString(190, 95, f"Código de Validação:")
        p.setFont("Helvetica-Oblique", 9)
        p.drawString(190, 80, verification_url)
        p.drawString(190, 65, "Acesse o Validador ITI ou leia o QRCode ao lado para verificar.")
        p.save()
        
        carimbo_buffer.seek(0)
        
        # 3. Mesclar (Carimbar) na primeira/última página do PDF original
        pdf_reader = PdfReader(BytesIO(pdf_original_bytes))
        carimbo_reader = PdfReader(carimbo_buffer)
        
        pdf_writer = PdfWriter()
        carimbo_page = carimbo_reader.pages[0]
        
        # Como o QR code fica no rodapé, apenas fazemos merge na primeira página:
        for i in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[i]
            if i == 0: 
                page.merge_page(carimbo_page)
            pdf_writer.add_page(page)
            
        final_buffer = BytesIO()
        pdf_writer.write(final_buffer)
        return final_buffer.getvalue()

