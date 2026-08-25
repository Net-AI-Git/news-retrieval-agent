from fastapi import APIRouter, Depends
from fastapi.openapi.docs import get_swagger_ui_html

from ..config import settings
from ..dependencies import require_docs_credentials


router = APIRouter()


@router.get("/docs", include_in_schema=False)
async def get_documentation(credentials = Depends(require_docs_credentials)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title=settings.project_name, swagger_js_url="/static/swagger-ui-bundle.js", swagger_css_url="/static/swagger-ui.css")
