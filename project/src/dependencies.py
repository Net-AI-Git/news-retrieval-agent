import os

from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic
from starlette.status import HTTP_401_UNAUTHORIZED

from .config import settings


docs_security = HTTPBasic()


async def get_blob_client():
    account_url = os.getenv("AZURE_STORAGE_URL")
    credential = AzureNamedKeyCredential(name=os.getenv("AZURE_STORAGE_ID"), key=os.getenv("AZURE_STORAGE_KEY"))
    async with AsyncBlobServiceClient(account_url, credential=credential) as blob_service_client:
        yield blob_service_client


def require_docs_credentials(credentials = Depends(docs_security)):
    if not settings.docs_pass or credentials.username != settings.docs_user or credentials.password != settings.docs_pass:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Basic"})
    return credentials
