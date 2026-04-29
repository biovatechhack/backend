from __future__ import annotations


class GeminiParseError(Exception):
    """Raised when the Gemini API returns a response that cannot be parsed."""


class GeminiUnavailableError(Exception):
    """Raised when all retry attempts to the Gemini API are exhausted."""


class PatientNotFoundError(Exception):
    """Raised when a patient_id does not match any record."""
