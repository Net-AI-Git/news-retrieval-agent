from fastapi import APIRouter, Depends, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBasic
from starlette.status import HTTP_401_UNAUTHORIZED

from ..config import settings


router = APIRouter()
security = HTTPBasic()


@router.get("/docs", include_in_schema=False)
async def get_documentation(credentials = Depends(security)):
    if not settings.docs_pass or credentials.username != settings.docs_user or credentials.password != settings.docs_pass:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Basic"})
    return get_swagger_ui_html(openapi_url="/openapi.json", title=settings.project_name, swagger_js_url="/static/swagger-ui-bundle.js", swagger_css_url="/static/swagger-ui.css")
