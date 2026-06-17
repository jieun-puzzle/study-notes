"""
Q&A 암기 & 랜덤 연습 앱

기능:
  1. 📚 회사별 정리 - 회사/카테고리별로 질문·답변 모아보기 + 검색
  2. 🧠 암기 모드   - 질문만 보고 답을 떠올린 뒤 펼쳐서 확인 + 암기 체크
  3. 🎲 랜덤 연습   - 무작위로 질문을 하나씩 출제 (실전 연습)

모바일 브라우저에서도 그대로 사용 가능.
"""

import json
import random
from pathlib import Path

import streamlit as st

DATA_PATH = Path(__file__).resolve().parent / "questions.json"

st.set_page_config(
    page_title="Study Notes",
    page_icon="📒",
    layout="centered",  # 모바일 친화적
    initial_sidebar_state="collapsed",
)


@st.cache_data
def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def company_badge(company: str) -> str:
    colors = {
        "엑셀리언트": "#2563eb",
        "올라핀테크": "#7c3aed",
        "압토솔": "#0891b2",
    }
    c = colors.get(company, "#64748b")
    return (
        f"<span style='background:{c};color:white;padding:2px 10px;"
        f"border-radius:12px;font-size:0.8rem;'>{company}</span>"
    )


def question_card(item, show_answer: bool):
    """질문 1개 표시. show_answer=False면 답변을 접어둔다."""
    badge = company_badge(item["company"])
    cat = item.get("category", "")
    st.markdown(
        f"{badge} &nbsp; <span style='color:#888;font-size:0.8rem;'>{cat}"
        + (f" · {item['tag']}" if item.get("tag") else "")
        + "</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"**Q. {item['question']}**")
    if show_answer:
        st.success(item["answer"])
        if item.get("link"):
            st.info("🔗 " + item["link"])
    else:
        with st.expander("💡 모범답변 보기"):
            st.success(item["answer"])
            if item.get("link"):
                st.info("🔗 " + item["link"])


# ---------------------------------------------------------------- 데이터 로드
data = load_data()
companies = sorted({d["company"] for d in data})

st.caption(f"총 {len(data)}개 항목 · {' / '.join(companies)}")

mode = st.radio(
    "모드 선택",
    ["📚 회사별 정리", "🧠 암기 모드", "🎲 랜덤 연습"],
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

# ================================================================ 1. 회사별 정리
if mode == "📚 회사별 정리":
    col1, col2 = st.columns(2)
    with col1:
        sel_company = st.selectbox("회사", ["전체"] + companies)
    filtered = [d for d in data if sel_company == "전체" or d["company"] == sel_company]

    cats = sorted({d["category"] for d in filtered})
    with col2:
        sel_cat = st.selectbox("카테고리", ["전체"] + cats)
    if sel_cat != "전체":
        filtered = [d for d in filtered if d["category"] == sel_cat]

    keyword = st.text_input("🔍 검색 (질문·답변 내 키워드)", placeholder="예: KPI, SQL, 이탈")
    if keyword:
        k = keyword.lower()
        filtered = [
            d for d in filtered
            if k in d["question"].lower() or k in d["answer"].lower()
        ]

    st.caption(f"{len(filtered)}개 질문")
    for item in filtered:
        question_card(item, show_answer=False)
        st.write("")

# ================================================================ 2. 암기 모드
elif mode == "🧠 암기 모드":
    # 회사 필터
    sel_company = st.selectbox("회사", ["전체"] + companies, key="memo_company")
    pool = [d for d in data if sel_company == "전체" or d["company"] == sel_company]

    if "memorized" not in st.session_state:
        st.session_state.memorized = set()

    done = len([d for d in pool if d["id"] in st.session_state.memorized])
    st.progress(done / len(pool) if pool else 0,
                text=f"암기 완료: {done} / {len(pool)}")

    hide_memorized = st.checkbox("암기 완료한 질문 숨기기")
    if hide_memorized:
        pool = [d for d in pool if d["id"] not in st.session_state.memorized]

    st.caption("질문을 보고 답을 떠올린 뒤, 펼쳐서 확인하세요.")
    for item in pool:
        is_done = item["id"] in st.session_state.memorized
        question_card(item, show_answer=False)
        checked = st.checkbox(
            "✅ 암기 완료", value=is_done, key=f"memo_{item['id']}"
        )
        if checked:
            st.session_state.memorized.add(item["id"])
        else:
            st.session_state.memorized.discard(item["id"])
        st.write("")

# ================================================================ 3. 랜덤 연습
elif mode == "🎲 랜덤 연습":
    sel_company = st.selectbox("회사", ["전체"] + companies, key="mock_company")
    pool = [d for d in data if sel_company == "전체" or d["company"] == sel_company]

    # 세션 상태 초기화
    if "mock_id" not in st.session_state or st.session_state.get("mock_pool") != sel_company:
        st.session_state.mock_pool = sel_company
        st.session_state.mock_id = random.choice(pool)["id"] if pool else None
        st.session_state.mock_reveal = False

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎲 다음 질문", use_container_width=True):
            st.session_state.mock_id = random.choice(pool)["id"]
            st.session_state.mock_reveal = False
    with col2:
        if st.button("👀 답변 보기", use_container_width=True):
            st.session_state.mock_reveal = True

    current = next((d for d in pool if d["id"] == st.session_state.mock_id), None)
    if current is None and pool:
        current = random.choice(pool)
        st.session_state.mock_id = current["id"]

    st.divider()
    if current:
        question_card(current, show_answer=st.session_state.get("mock_reveal", False))
        if not st.session_state.get("mock_reveal", False):
            st.caption("질문을 소리 내어 답해본 뒤 '답변 보기'를 누르세요.")
    else:
        st.warning("질문이 없습니다.")

st.divider()
st.caption("자료 수정: .md 편집 후 parse_md.py 재실행")
