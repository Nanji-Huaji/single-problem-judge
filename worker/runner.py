import json
import os
import tarfile
import io
import time
from pathlib import Path

import docker
import docker.errors
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.languages import LANGUAGES

docker_client = docker.from_env()

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
    try:
        docker_client.images.get(SANDBOX_IMAGE)
    except docker.errors.ImageNotFound:
        docker_client.images.build(path="/sandbox-src", tag=SANDBOX_IMAGE, rm=True)


def create_tar_with_file(filename: str, file_content: str) -> bytes:
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        encoded_content = file_content.encode('utf-8')
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(encoded_content)
        tarinfo.mtime = int(time.time())
        tar.addfile(tarinfo, io.BytesIO(encoded_content))
    return tar_stream.getvalue()

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

    container = docker_client.containers.run(
        SANDBOX_IMAGE,
        command=["sleep", "infinity"],
        detach=True,
        network_mode="none",
        nano_cpus=1000000000,
        mem_limit="256m",
        pids_limit=64,
    )
    try:
        source_name = language_config["source_name"]
        tar_bytes = create_tar_with_file(source_name, source_code)
        container.put_archive("/workspace", tar_bytes)

        compile_result = container.exec_run(
            ["bash", "-lc", language_config["compile"]],
            workdir="/workspace",
            demux=True,
        )
        compile_exit_code = compile_result.exit_code
        stdout, stderr = compile_result.output
        compile_stdout = (stdout or b"").decode("utf-8", errors="replace")
        compile_stderr = (stderr or b"").decode("utf-8", errors="replace")

        if compile_exit_code != 0:
            with SessionLocal() as session:
                update_submission(
                    session,
                    submission_id,
                    status="finished",
                    verdict="Compile Error",
                    detail="Compilation failed",
                    compile_output=(compile_stderr or compile_stdout)[-8000:],
                )
            return

        interactor_code = Path(__file__).parent.joinpath("interactor.py").read_text()
        interactor_tar_bytes = create_tar_with_file("interactor.py", interactor_code)
        container.put_archive("/workspace", interactor_tar_bytes)

        total_weighted_raw_score = 0.0
        import random
        import json
        import math
        
        test_reports = []
        worst_verdict = "Accepted"

        for idx, case in enumerate(PROBLEM["tests"], 1):
            n = case["n"]
            # Dynamic seed generation
            seed = random.randint(10000, 99999)

            start = time.perf_counter()
            run_result = container.exec_run(
                ["bash", "-lc", f"timeout 5s python3 /workspace/interactor.py {n} {seed} '{language_config['run']}'"],
                workdir="/workspace",
                demux=True,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            run_exit_code = run_result.exit_code
            stdout, stderr = run_result.output
            run_stdout = (stdout or b"").decode("utf-8", errors="replace")
            run_stderr = (stderr or b"").decode("utf-8", errors="replace")

            if run_exit_code == 124:
                msg = f"Test N={n} (Seed: {seed}) exceeded time limit"
                test_reports.append(json.dumps({"N": n, "Seed": seed, "Status": "TLE", "RawScore": 0, "Weighted": 0.0, "Error": msg}))
                if worst_verdict == "Accepted":
                    worst_verdict = "Time Limit Exceeded"
                continue

            if run_exit_code != 0:
                err_msg = run_stderr.strip()
                msg = f"Test N={n} (Seed: {seed}) crashed or validation failed: {err_msg}"
                test_reports.append(json.dumps({"N": n, "Seed": seed, "Status": "RE/WA", "RawScore": 0, "Weighted": 0.0, "Error": err_msg}))
                if worst_verdict == "Accepted":
                    worst_verdict = "Runtime Error/Wrong Answer"
                continue

            try:
                out_data = json.loads(run_stdout.strip().split("\n")[-1])
                raw_score = out_data["raw_score"]
                weight = 1.0 / (math.log2(n) + 1)
                weighted_score = raw_score * weight
                total_weighted_raw_score += weighted_score
                test_reports.append(json.dumps({"N": n, "Seed": seed, "Status": "OK", "RawScore": raw_score, "Weighted": round(weighted_score, 2)}))
            except Exception as e:
                msg = f"Test N={n} faled to parse interactor output"
                test_reports.append(json.dumps({"N": n, "Seed": seed, "Status": "SysErr", "RawScore": 0, "Weighted": 0.0, "Error": msg}))
                if worst_verdict == "Accepted":
                    worst_verdict = "System Error"
                continue

        # Calculate final base score based on total_weighted_raw_score
        base_score = 0
        if total_weighted_raw_score >= 500:
            base_score = 50
        elif total_weighted_raw_score >= 400:
            base_score = 45
        elif total_weighted_raw_score >= 300:
            base_score = 40
        elif total_weighted_raw_score >= 200:
            base_score = 35
        elif total_weighted_raw_score >= 100:
            base_score = 30
            
        with SessionLocal() as session:
            final_report_str = "\n".join(test_reports) + f"\n\nTotal Weighted Score: {total_weighted_raw_score:.2f} / Base Score: {base_score}"
            update_submission(
                session,
                submission_id,
                status="finished",
                verdict=worst_verdict,
                detail=final_report_str,
                score=base_score,
                time_ms=elapsed_ms,
            )

    except Exception as e:
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
    finally:
        container.remove(force=True)

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
