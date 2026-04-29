from typing import Optional

from fastapi import APIRouter, Depends, Header

from application.use_cases.conversation_usecase import ConversationUseCase
from domain.models.api_schemas import ConversationRequest, ConversationResponse
from presentation.api.dependencies import get_conversation_use_case

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/", response_model=ConversationResponse)
async def conversation_endpoint(
    request: ConversationRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    use_case: ConversationUseCase = Depends(get_conversation_use_case),
):
    """Patient sends a Darija message. Pass X-Session-ID header to continue an existing session."""
    return await use_case.execute(request, session_id=x_session_id)
