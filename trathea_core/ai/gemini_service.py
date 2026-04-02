"""
trathea_core/ai/gemini_service.py
Integração com a API Google Gemini para sugestões médicas de IA.
"""
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger("trathea")


class GeminiService:
    """
    Serviço de integração com o Google Gemini AI.

    Responsabilidades:
    - Sugestão de anamnese
    - Sugestão de diagnóstico
    - Sugestão de prescrição
    - Resumo de prontuário

    IMPORTANTE: As sugestões são de APOIO à decisão médica.
    O médico tem responsabilidade final sobre qualquer decisão clínica.
    """

    DISCLAIMER = (
        "⚠️ ATENÇÃO: Esta sugestão é gerada por IA e destina-se exclusivamente "
        "como apoio à decisão clínica. A responsabilidade final é do médico responsável."
    )

    def __init__(self):
        self._model = None
        self._initialized = False

    def _get_model(self):
        """Inicializa o modelo Gemini de forma lazy."""
        if not self._initialized:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._model = genai.GenerativeModel("gemini-2.5-flash")
                self._initialized = True
            except ImportError:
                raise GeminiUnavailableError("Biblioteca google-generativeai não instalada.")
            except Exception as e:
                raise GeminiUnavailableError(f"Erro ao inicializar Gemini: {e}")
        return self._model

    def _gerar_resposta(self, prompt: str) -> str:
        """Envia prompt para o Gemini e retorna a resposta."""
        try:
            model = self._get_model()
            response = model.generate_content(prompt)
            return response.text
        except GeminiUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise GeminiError(f"Erro ao processar solicitação com IA: {e}")

    def sugerir_anamnese(self, sintomas: list[str], historico: Optional[str] = None) -> dict:
        """
        Gera perguntas de anamnese com base nos sintomas relatados.

        Args:
            sintomas: Lista de sintomas do paciente.
            historico: Histórico médico relevante (opcional).

        Returns:
            Dicionário com perguntas sugeridas e observações.
        """
        prompt = f"""
        Você é um assistente médico especializado em anamnese.
        O paciente relata os seguintes sintomas: {', '.join(sintomas)}.
        {f'Histórico relevante: {historico}' if historico else ''}

        Gere 8 perguntas de anamnese focadas, objetivas e clinicamente relevantes.
        Organize por sistema (cardiovascular, respiratório, etc.).
        Responda em português, formato JSON:
        {{"perguntas": [{{"sistema": "...", "pergunta": "..."}}], "observacoes": "..."}}
        """
        resposta = self._gerar_resposta(prompt)
        return {"sugestao": resposta, "disclaimer": self.DISCLAIMER}

    def sugerir_diagnostico(self, sintomas: list[str], anamnese: str) -> dict:
        """
        Sugere hipóteses diagnósticas com base em sintomas e anamnese.

        Args:
            sintomas: Lista de sintomas.
            anamnese: Texto completo da anamnese.

        Returns:
            Hipóteses diagnósticas com CID10 sugerido.
        """
        prompt = f"""
        Você é um assistente médico. Com base nos dados clínicos abaixo,
        sugira as principais hipóteses diagnósticas com CID-10.

        Sintomas: {', '.join(sintomas)}
        Anamnese: {anamnese}

        Responda em português, formato JSON:
        {{"hipoteses": [{{"diagnostico": "...", "cid10": "...", "probabilidade": "alta|media|baixa"}}],
          "exames_sugeridos": ["..."], "observacoes": "..."}}

        Lembre-se: você é um APOIO, não um substituto ao julgamento médico.
        """
        resposta = self._gerar_resposta(prompt)
        return {"sugestao": resposta, "disclaimer": self.DISCLAIMER}

    def sugerir_prescricao(self, diagnostico: str, paciente_info: dict) -> dict:
        """
        Sugere prescrição com base no diagnóstico.

        Args:
            diagnostico: Diagnóstico principal.
            paciente_info: Info do paciente (idade, peso, alergias).

        Returns:
            Sugestão de medicamentos com dosagens.
        """
        alergias = paciente_info.get("alergias", "Nenhuma conhecida")
        idade = paciente_info.get("idade", "N/A")

        prompt = f"""
        Você é um assistente de prescrição médica.
        Diagnóstico: {diagnostico}
        Paciente: {idade} anos, alergias: {alergias}

        Sugira medicamentos com dosagem, posologia e duração do tratamento.
        Formato JSON:
        {{"medicamentos": [{{"nome": "...", "dosagem": "...", "posologia": "...",
          "duracao": "...", "observacoes": "..."}}], "alertas": ["..."]}}

        IMPORTANTE: Esta é apenas uma sugestão. Verifique interações medicamentosas.
        """
        resposta = self._gerar_resposta(prompt)
        return {"sugestao": resposta, "disclaimer": self.DISCLAIMER}

    def resumir_prontuario(self, prontuario_texto: str) -> dict:
        """
        Gera um resumo clínico do prontuário.

        Args:
            prontuario_texto: Texto completo do prontuário.

        Returns:
            Resumo estruturado do prontuário.
        """
        prompt = f"""
        Você é um médico assistente. Leia o prontuário abaixo e gere um resumo
        clínico estruturado, destacando pontos críticos.

        Prontuário:
        {prontuario_texto}

        Formato JSON:
        {{"resumo": "...", "pontos_criticos": ["..."], "medicamentos_em_uso": ["..."],
          "alergias_identificadas": ["..."], "proximos_passos_sugeridos": ["..."]}}
        """
        resposta = self._gerar_resposta(prompt)
        return {"sugestao": resposta, "disclaimer": self.DISCLAIMER}

    def estruturar_transcricao(self, transcricao_texto: str) -> dict:
        """
        Estrutura a transcrição bruta de uma consulta médica em linguagem médica formal.
        """
        import json
        prompt = f"""
Você é um assistente médico especializado em transcrição e organização de prontuários eletrônicos. Com base no áudio ou transcrição da consulta fornecida, gere um resumo clínico estruturado seguindo estas diretrizes:

Queixa Principal (QP): Relate de forma sucinta o motivo principal da consulta.
Anamnese/História Clínica: Sintetize o histórico da doença atual, sintomas relatados (tempo de início, intensidade, fatores de melhora/piora) e antecedentes relevantes.
Exame Físico (se disponível): Descreva os sinais vitais e achados pertinentes.
Hipótese Diagnóstica (HD): Liste as possibilidades diagnósticas baseadas no relato, utilizando terminologia médica adequada.
Conduta Médica: Descreva detalhadamente o plano de ação (exames solicitados, prescrições com posologia, orientações ao paciente e data de retorno).

Regra de Ouro: Se alguma informação não for mencionada na transcrição, escreva 'Não informado durante a consulta' em vez de deixar vago ou preencher com caracteres aleatórios. Mantenha um tom profissional, ético e conciso.
É estritamente PROIBIDO copiar as falas da transcrição. Você DEVE interpretar e reescrever as informações.

Analise a transcrição fornecida e retorne APENAS um objeto JSON válido, sem nenhum texto antes ou depois, seguindo esta estrutura exata:

{{
  "queixaPrincipal": "...",
  "anamnese": "...",
  "exameFisico": "...",
  "hipoteseDiagnostica": "...",
  "condutaMedica": "...",
  "medicamentos": [
    {{
      "nome": "string",
      "dosagem": "string (ex: 500mg, ou 'A definir')",
      "posologia": "string (ex: 1 cp 8/8h, ou 'A definir')",
      "quantidade": "string (ex: 1 caixa, ou 'A definir')",
      "via": "string (ex: oral, intravenoso, etc)"
    }}
  ]
}}

Transcrição bruta:
"{transcricao_texto}"
        """
        resposta_raw = self._gerar_resposta(prompt)
        resposta_clean = resposta_raw.replace("```json", "").replace("```", "").strip()
        
        try:
            dados = json.loads(resposta_clean)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao converter resposta IA para JSON: {e}. Resposta: {resposta_clean}")
            dados = {
                "queixa_principal": "Não foi possível extrair a queixa principal com precisão.",
                "anamnese": resposta_clean,
                "hipotese_diagnostica": "A avaliar",
                "medicamentos": []
            }
            
        return {"sugestao": dados, "disclaimer": self.DISCLAIMER}

class GeminiError(Exception):
    """Erro geral do serviço Gemini."""
    pass


class GeminiUnavailableError(GeminiError):
    """Serviço Gemini indisponível."""
    pass
