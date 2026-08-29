from typing import Optional

from pydantic import BaseModel


class Response(BaseModel):
    content: str
    flow_id: Optional[str] = None
    trace_id: Optional[str] = None
