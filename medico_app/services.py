"""
medico_app/services.py
Serviços dedicados a validações e regras de negócio do médico (SOLID: Single Responsibility).
"""
import requests
import hashlib

class MedicoValidationService:
    @staticmethod
    def validar_registro_profissional(crm: str, estado: str) -> bool:
        """
        Valida o formato e integridade básica do CRM/Estado.
        Poderia ser integrado a API do CFM (Conselho Federal de Medicina).
        """
        if not crm or not estado:
            return False
        if len(estado) != 2:
            return False
        if not crm.isdigit():
            return False
        return True


class SmartRxService:
    @staticmethod
    def calcular_dosagem(dose_base_mg: float, peso_kg: float) -> float:
        """
        Dose_{total} = Dose_{base} * Peso_{paciente}
        """
        if peso_kg <= 0 or dose_base_mg <= 0:
            return 0.0
        return dose_base_mg * peso_kg

    @staticmethod
    def validar_imc_seguro(peso_kg: float, altura_cm: float) -> dict:
        """Calcula o IMC e retorna alerta se estiver fora da faixa normal."""
        if not peso_kg or not altura_cm or altura_cm <= 0:
            return {"is_safe": True, "alert": None}
        
        altura_m = altura_cm / 100.0
        imc = peso_kg / (altura_m ** 2)
        
        if imc < 18.5:
            return {"is_safe": False, "imc": format(imc, ".1f"), "alert": "Atenção: Paciente está abaixo do peso ideal. Ajuste a dosagem com cautela."}
        elif imc > 30:
            return {"is_safe": False, "imc": format(imc, ".1f"), "alert": "Atenção: Paciente com obesidade (IMC alto). Verifique limite e acúmulo de toxicidade na dosagem."}
        
        return {"is_safe": True, "imc": format(imc, ".1f"), "alert": None}


class AssinaturaDigitalService:
    @staticmethod
    def gerar_hash_documento(conteudo_pdf_bytes: bytes) -> str:
        """Gera um Hash SHA-256 de integridade para o documento."""
        hasher = hashlib.sha256()
        hasher.update(conteudo_pdf_bytes)
        return hasher.hexdigest()

    @staticmethod
    def assinar_via_govbr(medico, documento_hash: str) -> dict:
        """
        Simula o fluxo OAuth2 de assinatura avançada pelo GOV.BR.
        Retorna metadados da assinatura.
        """
        if not MedicoValidationService.validar_registro_profissional(medico.crm, medico.crm_estado):
            raise ValueError("CRM não validado para assinatura.")

        # Simulação de integração com a API gov.br
        link_verificacao = f"https://verificador.iti.gov.br/?hash={documento_hash}"
        return {
            "status": "ASSINADO",
            "provider": "ICP-Brasil / GOV.BR",
            "hash": documento_hash,
            "verification_link": link_verificacao,
            "signed_by": f"Dr(a). {medico.user.nome_completo}"
        }


# ==========================================
# Factory Pattern: Catálogo por Profissional
# ==========================================
from abc import ABC, abstractmethod

class CatalogoMedicamento(ABC):
    @abstractmethod
    def obter_lista(self):
        pass

class CatalogoMedico(CatalogoMedicamento):
    """Catálogo Geral para Médicos"""
    def obter_lista(self):
        return [
            {"value": "", "label": "Selecione ou busque...", "dose_base_mg": ""},
            {"value": "amoxicilina", "label": "Amoxicilina (Antibiótico Amplo Espectro)", "dose_base_mg": 15},
            {"value": "dipirona", "label": "Dipirona Sódica (Analgésico Cefaleia/Febre)", "dose_base_mg": 10},
            {"value": "ibuprofeno", "label": "Ibuprofeno (AINE sistêmico)", "dose_base_mg": 8},
            {"value": "losartana", "label": "Losartana (Anti-hipertensivo)", "dose_base_mg": 1},
        ]

class CatalogoDentista(CatalogoMedicamento):
    """Catálogo Focado para Dentistas (Odontologia)"""
    def obter_lista(self):
        return [
            {"value": "", "label": "Selecione ou busque...", "dose_base_mg": ""},
            {"value": "amoxicilina", "label": "Amoxicilina (Infecção Odontológica)", "dose_base_mg": 15},
            {"value": "clindamicina", "label": "Clindamicina (Alérgico a Penicilina/Dente)", "dose_base_mg": 5},
            {"value": "paracetamol", "label": "Paracetamol (Dor pós-operatória/Extração)", "dose_base_mg": 12},
            {"value": "nimesulida", "label": "Nimesulida (Inflamação Gengival)", "dose_base_mg": 2},
        ]

class CatalogoFactory:
    @staticmethod
    def criar_catalogo(especialidade: str) -> CatalogoMedicamento:
        """Retorna o catálogo adequado injetando a regra de negócio correta."""
        especialidade_lower = especialidade.lower() if especialidade else ""
        if "odonto" in especialidade_lower or "dentista" in especialidade_lower or "buco" in especialidade_lower:
            return CatalogoDentista()
        return CatalogoMedico()
