from typing import Optional

from pydantic import BaseModel


class RetrievedItem(BaseModel):
    article_title: str
    snippet: str
    url: Optional[str] = None
    published_at: Optional[str] = None
    match_percentage: float


class SearchEvidenceInput(BaseModel):
    question: str
    published_from: Optional[str] = None
    published_to: Optional[str] = None


class SearchEvidenceOutput(BaseModel):
    status: str
    question: str
    results: list[RetrievedItem]


class AnswerCitation(BaseModel):
    article_title: str
    url: Optional[str] = None


class AnswerResult(BaseModel):
    status: str
    answer: str = ""
    citations: list[AnswerCitation] = []
