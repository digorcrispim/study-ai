from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MaterialCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    type: Literal["pdf", "video"]
    storage_path: str | None = None


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    type: str
    storage_path: str | None
    created_at: datetime


class QuestionCreate(BaseModel):
    material_id: UUID | None = None
    question_text: str = Field(min_length=1)
    options: dict[str, str]
    correct_answer: int = Field(ge=0)
    explanation: str | None = None
    topics: list[str] | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    material_id: UUID | None
    question_text: str
    options: dict[str, str]
    correct_answer: int
    explanation: str | None
    topics: list[str] | None
    difficulty: str | None
    created_at: datetime


class QuestionAnswer(BaseModel):
    selected_answer: int = Field(ge=0)


class UserAnswerCreate(BaseModel):
    user_id: UUID
    selected_answer: int = Field(ge=0)

class AdaptiveQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    options: dict[str, str]
    topics: list[str]
    difficulty: str
    explanation: str | None
class UserAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    question_id: UUID
    selected_answer: int
    is_correct: bool
    answered_at: datetime

    adaptive_questions: list[AdaptiveQuestionResponse] = Field(default_factory=list)


class UserAnswerSummaryResponse(BaseModel):
    user_id: UUID
    total_answers: int
    correct_answers: int
    incorrect_answers: int
    accuracy: float


class TopicPerformance(BaseModel):
    topic: str
    total_answers: int
    correct_answers: int
    incorrect_answers: int
    accuracy: float


class UserTopicPerformanceResponse(BaseModel):
    user_id: UUID
    topics: list[TopicPerformance]


class QuestionStudyResponse(BaseModel):
    id: UUID
    material_id: UUID | None
    question_text: str
    options: dict[str, str]
    topics: list[str] | None
    difficulty: str | None
    explanation: str | None


class MaterialTextUpdate(BaseModel):
    raw_text: str = Field(min_length=1)


class StudySessionCreate(BaseModel):
    user_id: UUID
    material_id: UUID
    mode: Literal["study", "review"]


class StudySessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    material_id: UUID
    mode: str
    started_at: datetime
    completed_at: datetime | None
    total_questions: int
    correct_answers: int
    accuracy: float


class StudySessionComplete(BaseModel):
    total_questions: int = Field(ge=0)
    correct_answers: int = Field(ge=0)


class QuestionGenerationRequest(BaseModel):
    number_of_questions: int = Field(default=5, ge=1, le=20)
