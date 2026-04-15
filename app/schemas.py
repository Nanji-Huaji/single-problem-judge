from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    source_code: str = Field(min_length=1, max_length=50000)
    language: str = Field(default="cpp17")


class SubmissionRead(BaseModel):
    id: int
    username: str
    language: str
    status: str
    verdict: str | None
    detail: str | None
    compile_output: str | None
    program_output: str | None
    expected_output: str | None
    time_ms: int | None
    memory_kb: int | None
    score: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProblemRead(BaseModel):
    slug: str
    title: str
    statement: str
    input_format: str
    output_format: str
    sample_input: str
    sample_output: str
    time_limit_ms: int
    memory_limit_mb: int
    supported_languages: list[str]
