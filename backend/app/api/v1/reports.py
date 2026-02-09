"""Report export endpoints.

POST /api/v1/reports/export - Export report as DOCX or PDF
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportExportRequest(BaseModel):
    """Request body for report export."""
    markdown_content: str
    format: Literal["docx", "pdf"]
    topic: str = "Report"


@router.post("/export")
async def export_report(request: ReportExportRequest) -> StreamingResponse:
    """Export a report as DOCX or PDF.

    Accepts markdown content and format, returns binary file.
    """
    from app.services.report_service import export_docx, export_pdf

    if not request.markdown_content.strip():
        raise HTTPException(status_code=400, detail="Markdown content is required")

    # Sanitize topic for filename
    safe_topic = "".join(c for c in request.topic if c.isalnum() or c in " -_")[:50].strip()
    if not safe_topic:
        safe_topic = "report"

    try:
        if request.format == "docx":
            buffer = export_docx(request.markdown_content, request.topic)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"{safe_topic}.docx"
        elif request.format == "pdf":
            # Convert markdown to HTML first for PDF
            import markdown
            html_content = markdown.markdown(
                request.markdown_content,
                extensions=["tables", "fenced_code", "nl2br"],
            )
            buffer = export_pdf(html_content, request.topic)
            media_type = "application/pdf"
            filename = f"{safe_topic}.pdf"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")

        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except ImportError as e:
        logger.error(f"Missing dependency for {request.format} export: {e}")
        raise HTTPException(
            status_code=501,
            detail=f"Export library not available: {e}. Install python-docx or weasyprint.",
        )
    except Exception as e:
        logger.error(f"Report export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)[:200]}")
