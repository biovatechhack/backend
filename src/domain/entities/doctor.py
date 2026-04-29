from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.entities.patient import Patient


@dataclass(slots=True)
class Doctor:
    id: str
    name: str
    email: str
    specialty: str
    clinic: str | None = None
    phone: str | None = None
    bio: str | None = None
    profile_picture_url: str | None = None
    experience_years: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    patients: list[Patient] = field(default_factory=list)
