from abstraction.ports.llm_port import LlmPort
from abstraction.ports.ml_port import RiskScorer
from abstraction.ports.notification_port import NotificationPort
from abstraction.repositories.patient_repository_port import PatientRepositoryPort
from application.use_cases.conversation_usecase import ConversationUseCase
from infrastructure.intelligence.adapters.deepseek_adapter import DeepSeekAdapter
from infrastructure.ml.real_risk_scorer import RealRiskScorer
from infrastructure.notifications.gmail_adapter import GmailNotificationAdapter
from infrastructure.supabase.patient_repository import SupabasePatientRepository


def get_llm() -> LlmPort:
    return DeepSeekAdapter()


def get_risk_scorer() -> RiskScorer:
    return RealRiskScorer()


def get_patient_repo() -> PatientRepositoryPort:
    return SupabasePatientRepository()


def get_notification_adapters() -> list[NotificationPort]:
    return [GmailNotificationAdapter()]


def get_conversation_use_case() -> ConversationUseCase:
    return ConversationUseCase(
        llm=get_llm(),
        risk_scorer=get_risk_scorer(),
        notifications=get_notification_adapters(),
        patient_repo=get_patient_repo(),
    )
