"""
trathea_core/signature/govbr_oauth.py
Integração OAuth2 com o Gov.br para obtenção de token de assinatura.

Documentação oficial:
    https://manual-roteiro-integracao-login-unico.servicos.gov.br/
    https://www.gov.br/conecta/catalogo/apis/assinatura-eletronica
"""
import logging
import secrets
import urllib.parse
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger("trathea")


class GovBrOAuthService:
    """
    Serviço para gerenciar o fluxo OAuth2 do Gov.br.

    Responsabilidades:
    - Gerar URL de autorização
    - Trocar código de autorização por token
    - Obter informações do usuário (CPF/sub)
    - Renovar token expirado
    """

    SCOPES = "openid profile email govbr_assinatura"

    def __init__(self):
        self.client_id = settings.GOVBR_CLIENT_ID
        self.client_secret = settings.GOVBR_CLIENT_SECRET
        self.redirect_uri = settings.GOVBR_REDIRECT_URI
        self.auth_url = settings.GOVBR_AUTH_URL
        self.token_url = settings.GOVBR_TOKEN_URL
        self.userinfo_url = settings.GOVBR_USERINFO_URL

    def gerar_url_autorizacao(self, state_token: str) -> str:
        """
        Gera a URL de redirecionamento para o Gov.br.

        Args:
            state_token: Token CSRF para validar o callback.

        Returns:
            URL completa para redirecionar o usuário.
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": self.SCOPES,
            "redirect_uri": self.redirect_uri,
            "state": state_token,
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def gerar_state_token(self) -> str:
        """Gera um token CSRF seguro para o fluxo OAuth2."""
        return secrets.token_urlsafe(32)

    def trocar_codigo_por_token(self, code: str) -> Optional[dict]:
        """
        Troca o authorization code por tokens de acesso.

        Args:
            code: Código retornado pelo Gov.br no callback.

        Returns:
            Dicionário com access_token, id_token, etc. ou None em caso de erro.
        """
        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=15,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error("Gov.br: timeout ao trocar código por token")
            raise GovBrTimeoutError("Gov.br indisponível. Tente novamente.")

        except requests.exceptions.HTTPError as e:
            logger.error(f"Gov.br: erro HTTP {e.response.status_code}: {e.response.text}")
            raise GovBrAuthError(f"Erro de autenticação no Gov.br: {e.response.status_code}")

        except Exception as e:
            logger.error(f"Gov.br: erro inesperado: {e}", exc_info=True)
            raise GovBrAuthError("Erro inesperado ao comunicar com o Gov.br.")

    def obter_informacoes_usuario(self, access_token: str) -> Optional[dict]:
        """
        Obtém informações do usuário autenticado via Gov.br.

        Args:
            access_token: Token de acesso obtido na troca.

        Returns:
            Dicionário com sub (CPF hash), name, email, etc.
        """
        try:
            response = requests.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error("Gov.br: timeout ao obter userinfo")
            raise GovBrTimeoutError("Gov.br indisponível.")

        except Exception as e:
            logger.error(f"Gov.br userinfo error: {e}", exc_info=True)
            raise GovBrAuthError("Erro ao obter dados do Gov.br.")

    def renovar_token(self, refresh_token: str) -> Optional[dict]:
        """
        Renova o access_token usando o refresh_token.

        Args:
            refresh_token: Token de renovação.

        Returns:
            Novo dicionário de tokens ou None.
        """
        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=15,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Gov.br refresh error: {e}", exc_info=True)
            return None


# ── Exceções Gov.br ──────────────────────────────────────────────────────────
class GovBrError(Exception):
    """Exceção base Gov.br."""
    pass


class GovBrTimeoutError(GovBrError):
    """Gov.br indisponível ou timeout."""
    pass


class GovBrAuthError(GovBrError):
    """Erro de autenticação ou autorização no Gov.br."""
    pass
