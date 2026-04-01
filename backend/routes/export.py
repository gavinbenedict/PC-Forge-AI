"""
PCForge AI — /export Routes
Streams CSV and Excel export files from inline analysis payload.
"""
from __future__ import annotations
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
import io

from backend.models.schemas import AnalyzeResponse
from backend.utils.exporter import export_csv, export_excel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["Export"])


@router.post("/excel")
async def download_excel(analysis: AnalyzeResponse) -> Response:
    """
    Generate and download a styled Excel workbook (.xlsx) for a given analysis.
    Contains 6 sheets: User Input, Final Build, Price Breakdown,
    Recommendations, Compatibility Report, Metadata.
    """
    try:
        excel_bytes = export_excel(analysis)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"PCForge_Build_{analysis.build_id}_{timestamp}.xlsx"

        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Build-ID": analysis.build_id,
            },
        )
    except Exception as e:
        logger.exception("Excel export failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/csv")
async def download_csv(analysis: AnalyzeResponse) -> Response:
    """
    Generate and download a flat CSV price breakdown for a given analysis.
    """
    try:
        csv_str = export_csv(analysis)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"PCForge_Build_{analysis.build_id}_{timestamp}.csv"

        return Response(
            content=csv_str.encode("utf-8"),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Build-ID": analysis.build_id,
            },
        )
    except Exception as e:
        logger.exception("CSV export failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
