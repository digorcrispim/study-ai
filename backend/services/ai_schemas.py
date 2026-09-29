from pydantic import BaseModel, Field


class GeneratedQuestion(BaseModel):
    question_text: str = Field(min_length=1)
    option_0: str = Field(min_length=1)
    option_1: str = Field(min_length=1)
    option_2: str = Field(min_length=1)
    option_3: str = Field(min_length=1)
    correct_answer: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=1)
    topics: list[str] = Field(min_length=1)
    difficulty: str = Field(min_length=1)


class GeneratedQuestionSet(BaseModel):
    questions: list[GeneratedQuestion] = Field(min_length=1)


class QuestionQualityReview(BaseModel):
    supported_by_material: bool
    single_correct_answer: bool
    clear_and_unambiguous: bool
    plausible_distractors: bool
    is_approved: bool
    reason: str = Field(min_length=1)


class QuestionQualityReviewSet(BaseModel):
    reviews: list[QuestionQualityReview] = Field(min_length=1)
