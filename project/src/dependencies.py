from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic
from starlette.status import HTTP_401_UNAUTHORIZED

from .config import settings


docs_security = HTTPBasic()


def require_docs_credentials(credentials = Depends(docs_security)):
    if not settings.docs_pass or credentials.username != settings.docs_user or credentials.password != settings.docs_pass:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Basic"})
    return credentials
