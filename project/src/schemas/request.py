from pydantic import BaseModel


class Request(BaseModel):
    content: str
