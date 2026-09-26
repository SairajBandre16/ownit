from __future__ import annotations

import re

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.deps import enforce_word_limit
from app.export.docx_writer import build_docx
from app.export.extract import MAX_BYTES, ExtractError, extract
from app.export.understanding_report import build_report
from app.schemas.export import ExportDocxRequest, ExtractResponse, UnderstandingReportRequest

router = APIRouter(tags=["export"])
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _filename(title: str, suffix: str = "") -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")[:60] or "document"
    return f"{slug}{suffix}.docx"


def _docx_response(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type=DOCX_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/files/extract", response_model=ExtractResponse)
async def files_extract(file: UploadFile = File(...)) -> ExtractResponse:
    data = await file.read(MAX_BYTES + 1)
    try:
        out = extract(file.filename or "", data)
    except ExtractError as e:
        status = 413 if len(data) > MAX_BYTES else 415 if "Only .docx" in str(e) else 422
        raise HTTPException(status_code=status, detail=str(e)) from e
    return ExtractResponse(text=out.text, words=out.words, warnings=out.warnings)


@router.post("/export/docx", response_class=Response)
def export_docx(body: ExportDocxRequest) -> Response:
    enforce_word_limit(body.text)
    data = build_docx(body.text, body.title.strip() or "Untitled", body.author, body.understanding)
    return _docx_response(data, _filename(body.title))


@router.post("/export/report", response_class=Response)
def export_report(body: UnderstandingReportRequest) -> Response:
    return _docx_response(build_report(body), _filename(body.title, "-understanding-report"))
