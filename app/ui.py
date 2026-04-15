import os
import time

import requests
import streamlit as st

from app.languages import LANGUAGES

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def fetch_problem() -> dict:
    response = requests.get(f"{API_BASE_URL}/problem", timeout=5)
    response.raise_for_status()
    return response.json()


def fetch_submissions() -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/submissions", timeout=5)
    response.raise_for_status()
    return response.json()


def submit_code(username: str, source_code: str, language: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/submissions",
        json={"username": username, "source_code": source_code, "language": language},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="Single Problem Judge", layout="wide")
st.title("Single Problem Judge")

problem = fetch_problem()

left, right = st.columns([3, 2])

with left:
    st.subheader(problem["title"])
    st.write(problem["statement"])
    st.markdown(f"**Input**: {problem['input_format']}")
    st.markdown(f"**Output**: {problem['output_format']}")
    st.markdown(f"**Time Limit**: {problem['time_limit_ms']} ms")
    st.markdown(f"**Memory Limit**: {problem['memory_limit_mb']} MB")
    st.code(problem["sample_input"], language="text")
    st.code(problem["sample_output"], language="text")

with right:
    username = st.text_input("Username", value="guest")
    supported_languages = [
        code for code in problem["supported_languages"] if code in LANGUAGES
    ]
    language = st.selectbox(
        "Language",
        supported_languages,
        format_func=lambda code: LANGUAGES[code]["label"],
    )
    source_code = st.text_area(
        f"{LANGUAGES[language]['label']} Code",
        value=LANGUAGES[language]["default_code"],
        height=420,
    )
    if st.button("Submit", type="primary"):
        result = submit_code(username, source_code, language)
        st.success(f"Submitted as #{result['id']}")

st.divider()
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("Refresh Results"):
        st.rerun()
    auto_refresh = st.checkbox("Auto refresh", value=True)
with col2:
    st.caption("Latest 50 submissions")

submissions = fetch_submissions()
st.dataframe(
    [
        {
            "id": item["id"],
            "user": item["username"],
            "language": item["language"],
            "status": item["status"],
            "verdict": item["verdict"],
            "time_ms": item["time_ms"],
            "created_at": item["created_at"],
            "detail": item["detail"],
        }
        for item in submissions
    ],
    use_container_width=True,
)

selected_id = st.number_input("Inspect submission id", min_value=1, step=1, value=1)
if st.button("Load Submission"):
    response = requests.get(f"{API_BASE_URL}/submissions/{selected_id}", timeout=5)
    if response.ok:
        item = response.json()
        st.write(item)
    else:
        st.error("Submission not found")

if auto_refresh:
    time.sleep(5)
    st.rerun()
