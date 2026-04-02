"""
trathea_core/signature/govbr_signature.py
Integração com a API de Assinatura Eletrônica do Gov.br (ITI).

Documentação:
    https://www.gov.br/conecta/catalogo/apis/assinatura-eletronica
    https://assinatura.staging.iti.br/externo/swagger-ui/
"""
import base64
import logging
from typing import Optional

import requests
from django.conf import settings

from trathea_core.signature.govbr_oauth import GovBrTimeoutError, GovBrError

logger = logging.getLogger("trathea")


class GovBrSignatureService:
    """
    Serviço de assinatura digital via API Gov.br (ITI).

    Responsabilidades:
    - Enviar hash do documento para o Gov.br assinar
    - Receber a assinatura PAdES de volta
    - Acoplar a assinatura ao PDF (via pdf_signer)
    """

    def __init__(self):
        self.signature_url = settings.GOVBR_SIGNATURE_URL

    def solicitar_assinatura_hash(
        self,
        hash_documento: str,
        access_token: str,
        algoritmo: str = "SHA256withRSA",
    ) -> bytes:
        """
        Envia o hash do documento para o Gov.br assinar.

        Args:
            hash_documento: Hash SHA-256 em hexadecimal do PDF.
            access_token: Token de acesso do Gov.br do médico.
            algoritmo: Algoritmo de assinatura (padrão: SHA256withRSA).

        Returns:
            Assinatura PAdES em bytes (base64 decodificado).

        Raises:
            GovBrSignatureError: Erro ao obter assinatura.
            GovBrTimeoutError: Gov.br indisponível.
        """
        payload = {
            "hashDocumento": hash_documento,
            "algoritmo": algoritmo,
            "tipoPdf": "ATTACHED",  # Assinatura embutida no PDF
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.signature_url,
                json=payload,
                headers=headers,
                timeout=30,  # Gov.br pode ser lento — timeout maior
            )
            response.raise_for_status()
            data = response.json()

            # Gov.br retorna a assinatura PAdES em base64
            assinatura_b64 = data.get("assinatura")
            if not assinatura_b64:
                raise GovBrSignatureError("Gov.br não retornou assinatura no payload.")

            return base64.b64decode(assinatura_b64)

        except requests.exceptions.Timeout:
            logger.error("Gov.br Signature: timeout")
            raise GovBrTimeoutError(
                "O serviço de assinatura do Gov.br está indisponível. "
                "A receita foi salva como rascunho. Tente assinar novamente em instantes."
            )

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            logger.error(f"Gov.br Signature: HTTP {status_code}: {e.response.text}")

            if status_code == 401:
                raise GovBrSignatureError(
                    "Token Gov.br expirado. Reautentique e tente novamente.", 
                    needs_reauth=True,
                )
            elif status_code == 403:
                raise GovBrSignatureError(
                    "Sem permissão de assinatura no Gov.br. Verifique sua conta."
                )
            else:
                raise GovBrSignatureError(
                    f"Erro {status_code} ao solicitar assinatura no Gov.br."
                )

        except GovBrError:
            raise

        except Exception as e:
            logger.error(f"Gov.br Signature: erro inesperado: {e}", exc_info=True)
            raise GovBrSignatureError("Erro inesperado ao solicitar assinatura.")


# ── Exceção ───────────────────────────────────────────────────────────────────
class GovBrSignatureError(GovBrError):
    """Erro durante o processo de assinatura digital no Gov.br."""

    def __init__(self, message: str, needs_reauth: bool = False):
        super().__init__(message)
        self.needs_reauth = needs_reauth
