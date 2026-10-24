"""Analyst console: GET /console serves a static page. Its data calls carry the analyst key itself."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

_ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(tags=["console"], include_in_schema=False)


@router.get("/console")
def console_page() -> FileResponse:
    return FileResponse(_ROOT / "api" / "static" / "console.html")


@router.get("/console/google_sans.ttf")
def console_font() -> FileResponse:
    # The app's bundled font (SIL Open Font License, see licenses/).
    return FileResponse(_ROOT / "app" / "src" / "main" / "res" / "font" / "google_sans.ttf")
