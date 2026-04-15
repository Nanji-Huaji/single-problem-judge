import os
import time

import requests
import streamlit as st
from streamlit_ace import st_ace
from streamlit_javascript import st_javascript

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


st.set_page_config(page_title="单题判题系统", layout="wide")
st.title("单题判题系统")

problem = fetch_problem()

left, right = st.columns([3, 2])

with left:
    st.subheader(problem["title"])
    st.write(problem["statement"])
    st.markdown(f"**输入格式**: {problem['input_format']}")
    st.markdown(f"**输出格式**: {problem['output_format']}")
    st.markdown(f"**时间限制**: {problem['time_limit_ms']} ms")
    st.markdown(f"**内存限制**: {problem['memory_limit_mb']} MB")
    st.code(problem["sample_input"], language="text")
    st.code(problem["sample_output"], language="text")

with right:
    username = st.text_input("用户名", value="guest")
    supported_languages = [
        code for code in problem["supported_languages"] if code in LANGUAGES
    ]
    language = st.selectbox(
        "编程语言",
        supported_languages,
        format_func=lambda code: LANGUAGES[code]["label"],
    )
    
    st.write(f"**请输入 {LANGUAGES[language]['label']} 代码:**")
    
    # Use javascript to detect Streamlit theme mode
    is_dark_mode = st_javascript('window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches')
    ace_theme = "monokai" if is_dark_mode else "chrome"

    source_code = st_ace(
        value=LANGUAGES[language]["default_code"],
        language=LANGUAGES[language]["editor_language"],
        theme=ace_theme,
        height=420,
        font_size=14,
        key=f"editor_{language}",
        auto_update=True
    )
    
    if st.button("提交代码", type="primary"):
        result = submit_code(username, source_code, language)
        st.success(f"提交成功，ID: #{result['id']}")

st.divider()
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("刷新结果"):
        st.rerun()
    auto_refresh = st.checkbox("自动刷新", value=True)
with col2:
    st.caption("最近 50 次提交")

def render_table():
    submissions = fetch_submissions()
    st.dataframe(
        [
            {
                "ID": item["id"],
                "用户": item["username"],
                "语言": item["language"],
                "状态": item["status"],
                "运行结果": item["verdict"],
                "耗时(ms)": item["time_ms"],
                "提交时间": item["created_at"],
                "详情": item["detail"],
            }
            for item in submissions
        ],
        use_container_width=True,
    )

if auto_refresh:
    @st.fragment(run_every=5)
    def auto_render_table():
        render_table()
    auto_render_table()
else:
    render_table()

st.divider()
selected_id = st.number_input("查看提交 ID", min_value=1, step=1, value=1)
if st.button("加载提交详情"):
    response = requests.get(f"{API_BASE_URL}/submissions/{selected_id}", timeout=5)
    if response.ok:
        item = response.json()
        st.write(item)
    else:
        st.error("未找到该提交")
