"""
tests/conftest.py
Fixtures globais compartilhadas por todos os testes do Tratta Backend.
"""
import pytest
from datetime import date, time, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APIClient

from core_app.models import CustomUser, UserProfile


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE: API Client
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    """APIClient limpo, sem autenticação."""
    return APIClient()


@pytest.fixture
def auth_client(client, usuario_medico):
    """APIClient autenticado como médico."""
    client.force_authenticate(user=usuario_medico)
    return client


@pytest.fixture
def admin_client(client, usuario_admin):
    """APIClient autenticado como admin."""
    client.force_authenticate(user=usuario_admin)
    return client


@pytest.fixture
def paciente_client(client, usuario_paciente):
    """APIClient autenticado como paciente."""
    client.force_authenticate(user=usuario_paciente)
    return client


@pytest.fixture
def clinica_client(client, usuario_clinica):
    """APIClient autenticado como clínica."""
    client.force_authenticate(user=usuario_clinica)
    return client


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE: Usuários
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def usuario_admin(db):
    """Cria um usuário admin."""
    user = CustomUser.objects.create_superuser(
        email="admin@tratta.app",
        password="Admin@Segura123",
        nome_completo="Administrador Tratta",
    )
    UserProfile.objects.create(user=user, cpf="52998224725")
    return user


@pytest.fixture
def usuario_medico(db):
    """Cria um usuário médico."""
    user = CustomUser.objects.create_user(
        email="dr.silva@tratta.app",
        password="Senha@Segura123",
        nome_completo="Dr. Carlos Silva",
        role="medico",
    )
    UserProfile.objects.create(user=user, cpf="98765432100")
    return user


@pytest.fixture
def usuario_paciente(db):
    """Cria um usuário paciente."""
    user = CustomUser.objects.create_user(
        email="paciente@tratta.app",
        password="Senha@Segura123",
        nome_completo="Maria Santos",
        role="paciente",
    )
    UserProfile.objects.create(user=user, cpf="11144477735")
    return user


@pytest.fixture
def usuario_clinica(db):
    """Cria um usuário clínica."""
    user = CustomUser.objects.create_user(
        email="clinica@tratta.app",
        password="Senha@Segura123",
        nome_completo="Clínica Saúde Total",
        role="clinica",
    )
    UserProfile.objects.create(user=user, cpf=None)
    return user


@pytest.fixture
def usuario_secretaria(db, clinica):
    """Cria um usuário secretaria vinculado a uma clínica."""
    from clinica_app.models import Secretaria

    user = CustomUser.objects.create_user(
        email="secretaria@tratta.app",
        password="Senha@Segura123",
        nome_completo="Ana Secretária",
        role="secretaria",
    )
    UserProfile.objects.create(user=user, cpf="82526711008")
    Secretaria.objects.create(
        user=user,
        clinica=clinica,
        cargo="Recepcionista",
        pode_agendar=True,
        pode_ver_prontuario=False,
    )
    return user


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE: Domínio — Médico
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def medico(usuario_medico):
    """Cria o perfil Medico vinculado ao usuário médico."""
    from medico_app.models import Medico

    return Medico.objects.create(
        user=usuario_medico,
        crm="123456",
        crm_estado="SP",
        especialidade="Clínica Geral",
        rqe="78901",
        bio="Médico generalista com 10 anos de experiência.",
        atende_convenio=True,
    )


@pytest.fixture
def disponibilidade(medico):
    """Cria uma disponibilidade para o médico (segunda-feira)."""
    from medico_app.models import Disponibilidade

    return Disponibilidade.objects.create(
        medico=medico,
        dia_semana=0,  # Segunda-feira
        hora_inicio=time(8, 0),
        hora_fim=time(12, 0),
        duracao_consulta_min=30,
        ativo=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE: Domínio — Clínica
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def clinica(usuario_clinica):
    """Cria o perfil Clinica vinculado ao usuário clínica."""
    from clinica_app.models import Clinica

    return Clinica.objects.create(
        user=usuario_clinica,
        nome_fantasia="Clínica Saúde Total",
        razao_social="Saúde Total LTDA",
        cnpj="11222333000181",
        telefone="(11) 3456-7890",
        email_contato="contato@saudetotal.com",
        endereco="Rua das Flores, 100 - São Paulo/SP",
        horario_funcionamento="Seg-Sex 08:00-18:00",
        ativa=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE: Domínio — Paciente
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def paciente(usuario_paciente):
    """Cria o perfil Paciente vinculado ao usuário paciente."""
    from paciente_app.models import Paciente

    return Paciente.objects.create(
        user=usuario_paciente,
        data_nascimento=date(1990, 5, 15),
        tipo_sanguineo="O+",
        peso_kg=Decimal("70.50"),
        altura_cm=175,
        alergias="Dipirona",
        doencas_cronicas="Nenhuma",
        medicamentos_uso_continuo="",
        convenio_nome="Unimed",
        convenio_numero="123456789",
    )


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE: Domínio — Consulta e Agendamento
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def agendamento(paciente, medico, clinica):
    """Cria um agendamento de teste."""
    from consulta_app.models import Agendamento

    return Agendamento.objects.create(
        paciente=paciente,
        medico=medico,
        clinica=clinica,
        data_hora=timezone.now() + timedelta(days=7),
        motivo="Consulta de rotina",
        status="pendente",
        criado_por=paciente.user,
    )


@pytest.fixture
def consulta(paciente, medico, agendamento):
    """Cria uma consulta em andamento."""
    from consulta_app.models import Consulta

    return Consulta.objects.create(
        agendamento=agendamento,
        paciente=paciente,
        medico=medico,
        data_inicio=timezone.now(),
        status="em_andamento",
        resumo="Paciente relata dores de cabeça frequentes.",
    )


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE: Domínio — Prescrição
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def medicamento(db):
    """Cria um medicamento simples de teste."""
    from prescricao_app.models import Medicamento

    return Medicamento.objects.create(
        nome="Paracetamol",
        principio_ativo="Paracetamol",
        concentracao="500mg",
        forma_farmaceutica="Comprimido",
        tipo="simples",
        ativo=True,
    )


@pytest.fixture
def medicamento_controlado(db):
    """Cria um medicamento controlado de teste."""
    from prescricao_app.models import Medicamento

    return Medicamento.objects.create(
        nome="Rivotril",
        principio_ativo="Clonazepam",
        concentracao="2mg",
        forma_farmaceutica="Comprimido",
        tipo="controlado",
        ativo=True,
    )


@pytest.fixture
def receita(medico, paciente, consulta, medicamento):
    """Cria uma receita rascunho com um item."""
    from prescricao_app.models import Receita, ItemReceita

    receita = Receita.objects.create(
        medico=medico,
        paciente=paciente,
        consulta=consulta,
        tipo="simples",
        status="rascunho",
        observacoes="Tomar com água.",
        validade_dias=30,
    )
    ItemReceita.objects.create(
        receita=receita,
        medicamento=medicamento,
        dosagem="500mg",
        quantidade="20 comprimidos",
        posologia="1 comprimido de 8/8h",
        via_administracao="oral",
        duracao_tratamento="7 dias",
        ordem=1,
    )
    return receita


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE: Domínio — Exames
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def tipo_exame(db):
    """Cria um tipo de exame de teste."""
    from exame_app.models import TipoExame

    return TipoExame.objects.create(
        nome="Hemograma Completo",
        descricao="Exame de sangue que avalia os componentes celulares.",
        codigo_cbhpm="40304361",
        requer_jejum=True,
        instrucoes_preparo="Jejum de 8 horas.",
    )


@pytest.fixture
def solicitacao_exame(consulta, paciente, medico, tipo_exame):
    """Cria uma solicitação de exame de teste."""
    from exame_app.models import SolicitacaoExame

    return SolicitacaoExame.objects.create(
        consulta=consulta,
        paciente=paciente,
        medico=medico,
        tipo_exame=tipo_exame,
        status="solicitado",
        urgente=False,
        instrucoes="Realizar em jejum de 8 horas.",
    )
