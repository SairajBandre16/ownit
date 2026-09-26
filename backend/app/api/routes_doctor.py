from __future__ import annotations

from fastapi import APIRouter

from app.deps import cached, enforce_word_limit
from app.doctor.service import run_doctor
from app.schemas.common import TextRequest
from app.schemas.doctor import DoctorResponse

router = APIRouter(tags=["doctor"])


def doctor_text(text: str) -> DoctorResponse:
    issues, counts = run_doctor(text)
    return DoctorResponse(issues=issues, counts=counts)


@router.post("/doctor", response_model=DoctorResponse)
def doctor(body: TextRequest) -> DoctorResponse:
    enforce_word_limit(body.text)
    return cached("doctor", {"text": body.text}, lambda: doctor_text(body.text))
