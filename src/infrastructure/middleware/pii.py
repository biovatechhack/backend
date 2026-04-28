import re
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict

class PiiMiddleware(BaseHTTPMiddleware):
    """
    PII De-identification Middleware (Sprint 1 P0)
    Replaces real names, phones, IDs with tokens before any LLM call.
    Mapping is stored in memory (Redis in production).
    """

    # Simple regex patterns for Algerian context
    PII_PATTERNS = {
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b': '[PATIENT]',           # Full name (Haj Ahmed, Fatima Benali...)
        r'0[5-7]\d{8}': '[PHONE]',                             # Algerian phone
        r'\b\d{10,12}\b': '[ID]',                              # CIN or other ID
    }

    def __init__(self, app):
        super().__init__(app)
        self.token_map: Dict[str, str] = {}   # In-memory for now (later → Redis)

    async def dispatch(self, request: Request, call_next):
        # Only apply to conversation endpoints
        if "/conversation" not in request.url.path and "/test-llm" not in request.url.path:
            return await call_next(request)

        # Read body
        body = await request.body()
        text = body.decode("utf-8", errors="ignore")

        # De-identify
        deidentified_text, mapping = self._deidentify(text)

        # Store mapping temporarily (for demo)
        request.state.pii_mapping = mapping

        # Replace body with de-identified version
        modified_request = Request(request.scope, receive=self._make_receive(deidentified_text.encode()))

        response = await call_next(modified_request)

        # For debugging: you can log the mapping
        if hasattr(request.state, "pii_mapping"):
            print(f"🔒 PII de-identified. Mapping: {mapping}")

        return response

    def _deidentify(self, text: str) -> tuple[str, Dict[str, str]]:
        mapping = {}
        deidentified = text
        for pattern, token in self.PII_PATTERNS.items():
            for match in re.findall(pattern, text):
                if match not in mapping:
                    mapping[match] = token
                deidentified = deidentified.replace(match, token)
        return deidentified, mapping

    def _make_receive(self, body: bytes):
        async def receive():
            return {"type": "http.request", "body": body}
        return receive