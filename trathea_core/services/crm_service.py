import datetime
import re

def consultar_cfm_mock(crm: str, uf: str, nome_digitado: str = "") -> dict:
    """
    Mock de consulta ao Conselho Federal de Medicina (CFM) ou Portal da Transparência.
    Valida se o CRM está Ativo, Inativo ou Inexistente, e retorna o nome oficial e especialidade (RQE).
    """
    crm_clean = re.sub(r"\D", "", crm)
    
    # 1. Caso inválido (vazio)
    if not crm_clean:
        return {
            "status": "Inexistente",
            "nome_oficial": "",
            "especialidade": "",
            "rqe": ""
        }
        
    resultado = {
        "status": "Ativo",
        "nome_oficial": nome_digitado.upper() if nome_digitado else f"MÉDICO VALIDADO CRM {crm_clean} {uf}",
        "especialidade": "Clínico Geral",
        "rqe": "RQE-99123"
    }

    # Condição de Teste 1: Terminado em 000 = Inativo (Barra na porta)
    if crm_clean.endswith("000"):
        resultado["status"] = "Inativo"
        resultado["nome_oficial"] = f"MÉDICO INATIVO CRM {crm_clean}"
        
    # Condição de Teste 2: Terminado em 404 = Inexistente (Barra na porta)
    elif crm_clean.endswith("404"):
        resultado["status"] = "Inexistente"
        resultado["nome_oficial"] = ""
        
    # Condição de Teste 3: Terminado em 999 = Nome diferente (Exibe divergência p/ Admin)
    elif crm_clean.endswith("999"):
        resultado["nome_oficial"] = "NOME TOTALMENTE DIFERENTE NO CFM DA SILVA"
        resultado["especialidade"] = "Cardiologista"
        
    return resultado
