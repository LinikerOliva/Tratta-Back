"""
medico_app/views_consulta.py
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error
from medico_app.services import SmartRxService, AssinaturaDigitalService, CatalogoFactory
from paciente_app.models import Paciente

@extend_schema(
    tags=["Consulta Médica"],
    summary="Carregar contexto do paciente",
    description="Retorna dados biométricos (peso, altura) e histórico de alergias."
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def carregar_contexto_paciente_view(request, paciente_id):
    try:
        paciente = Paciente.objects.get(id=paciente_id)
        return api_success(data={
            "peso_kg": paciente.peso_kg,
            "altura_cm": paciente.altura_cm,
            "alergias": paciente.alergias,
            "tipo_sanguineo": paciente.tipo_sanguineo
        })
    except Paciente.DoesNotExist:
        return api_error("Paciente não encontrado.", http_status=404)

@extend_schema(
    tags=["Consulta Médica"],
    summary="Smart Rx: Validar dosagem",
    description="Calcula a dosagem com base no peso do paciente e gera alertas se IMC fora do padrão."
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def calcular_dosagem_view(request):
    dose_base_mg = float(request.data.get("dose_base_mg", 0))
    peso_kg = float(request.data.get("peso_kg", 0))
    altura_cm = float(request.data.get("altura_cm", 0))

    if dose_base_mg <= 0:
        return api_error("Dose base inválida.", http_status=400)

    dose_total = SmartRxService.calcular_dosagem(dose_base_mg, peso_kg)
    imc_validation = SmartRxService.validar_imc_seguro(peso_kg, altura_cm)

    return api_success(data={
        "dose_total_mg": dose_total,
        "imc": imc_validation.get("imc"),
        "is_safe": imc_validation.get("is_safe"),
        "alerta_seguranca": imc_validation.get("alert")
    })

@extend_schema(
    tags=["Consulta Médica"],
    summary="Assinatura GOV.BR Callback",
    description="Recebe o callback OAuth2 do Gov.BR, obtém o token, assina e carimba o PDF."
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assinar_receita_govbr_view(request):
    medico = getattr(request.user, "medico", None)
    if not medico:
        return api_error("Você não é um médico.", http_status=403)

    code = request.data.get("code")
    state = request.data.get("state")
    
    if not code or not state:
        return api_error("Code e State do OAuth2 são obrigatórios.", http_status=400)
    
    try:
        from trathea_core.signature.govbr import GovBrSignatureIntegration
        from prescricao_app.models import Receita
        from django.core.files.base import ContentFile
        from django.utils import timezone
        
        # 1. Processa Token e Assina no ITI
        resultado = GovBrSignatureIntegration.processar_callback(code, state)
        hash_original = resultado["hash_original"]
        verify_url = resultado["verification_url"]
        
        receita = Receita.objects.get(hash_conteudo=hash_original)
        
        # 2. Carimbar o PDF original com QR Code
        if receita.pdf:
            pdf_original_bytes = receita.pdf.read()
            pdf_assinado_bytes = GovBrSignatureIntegration.carimbar_pdf(pdf_original_bytes, verify_url)
            
            # Salvar novo arquivo assinado
            nome_arquivo = f"receita_{receita.id}_assinada.pdf"
            receita.pdf.save(nome_arquivo, ContentFile(pdf_assinado_bytes))
            
            receita.status = Receita.Status.ASSINADA
            receita.via_govbr = True
            receita.assinada_em = timezone.now()
            receita.hash_verificacao = verify_url.split("=")[-1]
            receita.assinatura_govbr = resultado["artefato"].encode()
            receita.save()
            
        return api_success(data=resultado, message="Documento Assinado com Sucesso!")
    except Exception as e:
        return api_error(str(e), http_status=400)


@extend_schema(
    tags=["Consulta Médica"],
    summary="Catálogo de Medicamentos Dinâmico (Factory Pattern)",
    description="Retorna um catálogo focado dependendo do perfil (Odontologia vs Medicina)."
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalogo_medicamentos_view(request):
    medico = getattr(request.user, "medico", None)
    especialidade = medico.especialidade if medico else "Clínico Geral"
    
    catalogo_obj = CatalogoFactory.criar_catalogo(especialidade)
    
    return api_success(data={
        "especialidade_detectada": especialidade,
        "catalogo": catalogo_obj.obter_lista()
    })
