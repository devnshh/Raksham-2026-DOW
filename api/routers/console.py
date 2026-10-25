"""Analyst console: GET /console serves a static page. Its data calls carry the analyst key itself."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

_ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(tags=["console"], include_in_schema=False)


# Built from console-ui/ (React + bklit charts) by `npm run build`; the build output is committed so
# the demo needs no Node and works offline.
CONSOLE_DIR = _ROOT / "api" / "static" / "console"


@router.get("/console")
def console_page() -> FileResponse:
    return FileResponse(CONSOLE_DIR / "index.html")


@router.get("/console/inter.ttf")
def console_inter_font() -> FileResponse:
    # Inter, bundled so the console works offline (SIL Open Font License, see licenses/inter_OFL.txt).
    return FileResponse(_ROOT / "api" / "static" / "fonts" / "Inter.ttf", media_type="font/ttf")


@router.get("/console/google_sans.ttf")
def console_font() -> FileResponse:
    # The app's bundled font (SIL Open Font License, see licenses/).
    return FileResponse(_ROOT / "app" / "src" / "main" / "res" / "font" / "google_sans.ttf")
