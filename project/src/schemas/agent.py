from typing import Literal, Optional

from pydantic import BaseModel, model_validator

from ..conts import ANSWER_REFUSAL_TEXT, GRADE_VERDICT_EMPTY_STOP, GRADE_VERDICT_ENOUGH, GRADE_VERDICT_MISSING_HOP


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
    source: Optional[str] = None


class SearchEvidenceOutput(BaseModel):
    status: str
    question: str
    results: list[RetrievedItem]


class AnswerCitation(BaseModel):
    article_title: str
    url: Optional[str] = None
    snippet: str


class AnswerResult(BaseModel):
    status: str
    answer: str = ""
    citations: list[AnswerCitation] = []


class GatherResult(BaseModel):
    sub_questions: list[str]


class GradeResult(BaseModel):
    verdict: Literal[GRADE_VERDICT_ENOUGH, GRADE_VERDICT_MISSING_HOP, GRADE_VERDICT_EMPTY_STOP]
    note: str = ""


class SolutionCitation(BaseModel):
    article_title: str
    snippet: str


class SolutionAnswer(BaseModel):
    answer: str = ""
    citations: list[SolutionCitation] = []

    @model_validator(mode="after")
    def apply_refusal_answer(self):
        if not self.answer.strip():
            self.answer = ANSWER_REFUSAL_TEXT
        return self
