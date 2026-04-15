import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.languages import LANGUAGES


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/judge.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
JUDGE_QUEUE = os.getenv("JUDGE_QUEUE", "submissions")
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "sandbox-runner:latest")

engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


def ensure_image() -> None:
    result = subprocess.run(
        ["docker", "image", "inspect", SANDBOX_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        return
    subprocess.run(
        ["docker", "build", "-t", SANDBOX_IMAGE, "/sandbox-src"],
        check=True,
    )


def load_submission(session, submission_id: int):
    from app.models import Submission

    row = session.get(Submission, submission_id)
    if row is None:
        return None
    return row


def update_submission(session, submission_id: int, **fields) -> None:
    from app.models import Submission

    row = session.get(Submission, submission_id)
    if row is None:
        return
    for key, value in fields.items():
        setattr(row, key, value)
    session.add(row)
    session.commit()


def judge_submission(submission_id: int) -> None:
    from app.problem import PROBLEM

    with SessionLocal() as session:
        submission = load_submission(session, submission_id)
        if submission is None:
            return
        update_submission(
            session,
            submission_id,
            status="running",
            verdict="Running",
            detail="Compiling and testing",
        )
        source_code = submission.source_code
        language = submission.language

    language_config = LANGUAGES.get(language)
    if language_config is None:
        with SessionLocal() as session:
            update_submission(
                session,
                submission_id,
                status="finished",
                verdict="System Error",
                detail=f"Unsupported language: {language}",
            )
        return

    ensure_image()

    with tempfile.TemporaryDirectory(prefix=f"judge-{submission_id}-") as temp_dir:
        temp_path = Path(temp_dir)
        source_path = temp_path / language_config["source_name"]
        source_path.write_text(source_code, encoding="utf-8")

        compile_cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cpus",
            "1",
            "--memory",
            "256m",
            "-v",
            f"{temp_dir}:/workspace",
            SANDBOX_IMAGE,
            "bash",
            "-lc",
            language_config["compile"],
        ]
        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True)
        if compile_proc.returncode != 0:
            with SessionLocal() as session:
                update_submission(
                    session,
                    submission_id,
                    status="finished",
                    verdict="Compile Error",
                    detail="Compilation failed",
                    compile_output=(compile_proc.stderr or compile_proc.stdout)[-8000:],
                )
            return

        for case in PROBLEM["tests"]:
            input_path = temp_path / "input.txt"
            input_path.write_text(case["input"], encoding="utf-8")
            start = time.perf_counter()
            run_cmd = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--cpus",
                "1",
                "--memory",
                "256m",
                "--pids-limit",
                "64",
                "-v",
                f"{temp_dir}:/workspace",
                SANDBOX_IMAGE,
                "bash",
                "-lc",
                f"timeout 2s {language_config['run']} < /workspace/input.txt",
            ]
            run_proc = subprocess.run(run_cmd, capture_output=True, text=True)
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            if run_proc.returncode == 124:
                with SessionLocal() as session:
                    update_submission(
                        session,
                        submission_id,
                        status="finished",
                        verdict="Time Limit Exceeded",
                        detail="Program exceeded 2 seconds",
                        program_output=run_proc.stdout[-8000:],
                        expected_output=case["output"],
                        time_ms=elapsed_ms,
                    )
                return

            if run_proc.returncode != 0:
                with SessionLocal() as session:
                    update_submission(
                        session,
                        submission_id,
                        status="finished",
                        verdict="Runtime Error",
                        detail=(
                            run_proc.stderr or "Program exited with non-zero status"
                        )[-8000:],
                        program_output=run_proc.stdout[-8000:],
                        expected_output=case["output"],
                        time_ms=elapsed_ms,
                    )
                return

            actual = run_proc.stdout
            if actual != case["output"]:
                with SessionLocal() as session:
                    update_submission(
                        session,
                        submission_id,
                        status="finished",
                        verdict="Wrong Answer",
                        detail="Output does not match expected output",
                        program_output=actual[-8000:],
                        expected_output=case["output"],
                        time_ms=elapsed_ms,
                    )
                return

        with SessionLocal() as session:
            update_submission(
                session,
                submission_id,
                status="finished",
                verdict="Accepted",
                detail="All tests passed",
                program_output=None,
                expected_output=None,
                time_ms=elapsed_ms,
                memory_kb=None,
            )


def main() -> None:
    while True:
        _, payload = redis_client.blpop(JUDGE_QUEUE)
        data = json.loads(payload)
        try:
            judge_submission(int(data["submission_id"]))
        except Exception as exc:
            with SessionLocal() as session:
                update_submission(
                    session,
                    int(data["submission_id"]),
                    status="finished",
                    verdict="System Error",
                    detail=str(exc)[:8000],
                )


if __name__ == "__main__":
    main()
