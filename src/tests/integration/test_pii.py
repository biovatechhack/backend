import pytest
from infrastructure.middleware.pii import PiiMiddleware
from fastapi import Request

@pytest.mark.integration
async def test_pii_middleware():
    middleware = PiiMiddleware(app=None)  # dummy app for test

    # Simulate body with PII
    test_body = '{"text": "اسس بدوخة واسمي Haj Ahmed وهاتفي 0555123456"}'.encode('utf-8')
    
    # The middleware logic is tested via endpoint in real run
    # This is a unit-style test of _deidentify
    deidentified, mapping = middleware._deidentify(test_body.decode())

    assert "[PATIENT]" in deidentified
    assert "[PHONE]" in deidentified
    assert mapping  # mapping not empty
    print("✅ PII middleware test passed")