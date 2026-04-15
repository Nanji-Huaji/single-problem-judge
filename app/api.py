import json
import os

from fastapi import FastAPI, HTTPException
from redis import Redis
from sqlalchemy import select

from app.db import Base, engine, session_scope
from app.languages import LANGUAGES
from app.models import Submission
from app.problem import PROBLEM
from app.schemas import ProblemRead, SubmissionCreate, SubmissionRead


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
JUDGE_QUEUE = os.getenv("JUDGE_QUEUE", "submissions")

app = FastAPI(title="Single Problem Judge API")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/problem", response_model=ProblemRead)
def get_problem() -> ProblemRead:
    return ProblemRead(**{k: v for k, v in PROBLEM.items() if k != "tests"})


@app.post("/submissions", response_model=SubmissionRead)
def create_submission(payload: SubmissionCreate) -> SubmissionRead:
    if payload.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    with session_scope() as session:
        submission = Submission(
            username=payload.username.strip(),
            source_code=payload.source_code,
            language=payload.language,
            status="queued",
            verdict="Pending",
        )
        session.add(submission)
        session.flush()
        session.refresh(submission)
        redis_client.rpush(JUDGE_QUEUE, json.dumps({"submission_id": submission.id}))
        return SubmissionRead.model_validate(submission)


@app.get("/submissions", response_model=list[SubmissionRead])
def list_submissions() -> list[SubmissionRead]:
    with session_scope() as session:
        rows = (
            session.execute(select(Submission).order_by(Submission.id.desc()).limit(50))
            .scalars()
            .all()
        )
        return [SubmissionRead.model_validate(row) for row in rows]


@app.get("/submissions/{submission_id}", response_model=SubmissionRead)
def get_submission(submission_id: int) -> SubmissionRead:
    with session_scope() as session:
        submission = session.get(Submission, submission_id)
        if submission is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        return SubmissionRead.model_validate(submission)
