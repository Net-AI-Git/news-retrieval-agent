import os

from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient


async def get_blob_client():
    account_url = os.getenv("AZURE_STORAGE_URL")
    credential = AzureNamedKeyCredential(name=os.getenv("AZURE_STORAGE_ID"), key=os.getenv("AZURE_STORAGE_KEY"))
    async with AsyncBlobServiceClient(account_url, credential=credential) as blob_service_client:
        yield blob_service_client
