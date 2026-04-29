from fastapi import APIRouter, Depends, Header
from typing import Optional
from domain.models.api_schemas import ConversationRequest, ConversationResponse
from application.use_cases.conversation_usecase import ConversationUseCase
from presentation.api.dependencies import get_llm, get_risk_scorer

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/", response_model=ConversationResponse)
async def conversation_endpoint(
    request: ConversationRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),   # ← session_id from header
    use_case: ConversationUseCase = Depends(
        lambda: ConversationUseCase(
            llm=get_llm(),
            risk_scorer=get_risk_scorer()
        )
    ),
):
    """Patient sends message. session_id is passed in header X-Session-ID"""
    return await use_case.execute(request, session_id=x_session_id)