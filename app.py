"""
Q&A 암기 & 랜덤 연습 앱

기능:
  1. 📚 회사별 정리 - 회사/카테고리별로 질문·답변 모아보기 + 검색
  2. 🧠 암기 모드   - 질문만 보고 답을 떠올린 뒤 펼쳐서 확인 + 암기 체크
  3. 🎲 랜덤 연습   - 무작위로 질문을 하나씩 출제 (실전 연습)

모바일 브라우저에서도 그대로 사용 가능.
"""

import html
import json
import random
import re
from pathlib import Path

import streamlit as st

try:
    from streamlit_mic_recorder import mic_recorder
    _MIC_AVAILABLE = True
except ImportError:  # 라이브러리 미설치 환경에서도 앱이 죽지 않도록
    _MIC_AVAILABLE = False

DATA_PATH = Path(__file__).resolve().parent / "questions.json"

st.set_page_config(
    page_title="Study Notes",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data
def load_data(_mtime: float):
    # _mtime(파일 수정 시각)이 바뀌면 캐시가 자동 무효화되어 최신 데이터를 읽는다.
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


# 답변에서 자동으로 강조할 핵심 키워드 (기술 스택·지표·역할 등)
# 새 키워드를 추가하고 싶으면 이 목록에 넣으면 됨.
HIGHLIGHT_KEYWORDS = [
    # 언어/도구
    "Python", "파이썬", "SQL", "Airflow", "BigQuery", "GCS", "Pandas", "pandas",
    "MySQL", "MariaDB", "PostgreSQL", "Looker Studio", "루커 스튜디오", "태블로",
    "Tableau", "Gemini", "Claude", "React",
    # 지표/분석
    "MRR", "MAU", "DAU", "LTV", "ROAS", "CVR", "코호트", "퍼널", "전환율",
    "해지율", "잔존율", "재학습", "Z-스코어", "F1-Score", "Chi-square",
    "T-검정", "카이제곱", "A/B 테스트", "BEP",
    # 개념/역할
    "데이터 정합성", "데이터 추출", "데이터 마트", "파이프라인", "KPI",
    "PO", "PO 역할", "피처 엔지니어링", "코호트 분석", "퍼널 분석",
    "데이터 품질", "전처리", "노이즈", "user_id",
]

# 긴 키워드부터 매칭(부분 중복 방지)
_HL_SORTED = sorted(set(HIGHLIGHT_KEYWORDS), key=len, reverse=True)
_HL_PATTERN = re.compile("|".join(re.escape(k) for k in _HL_SORTED))


def highlight(text: str) -> str:
    """텍스트를 HTML로 변환하며 핵심 키워드를 볼드+색상으로 강조한다."""
    escaped = html.escape(text)

    def repl(m):
        return (
            "<span style='color:#1d4ed8;font-weight:700;"
            "background:#eff6ff;padding:0 2px;border-radius:3px;'>"
            f"{m.group(0)}</span>"
        )

    highlighted = _HL_PATTERN.sub(repl, escaped)
    # 줄바꿈 유지
    return highlighted.replace("\n", "<br>")


def render_answer(text: str):
    """모범답변을 옅은 회색 테두리 박스 + 키워드 강조로 렌더링 (배경색 없음)."""
    st.markdown(
        "<div style='border:1px solid #e5e7eb;background:transparent;"
        "padding:12px 14px;border-radius:6px;line-height:1.7;'>"
        f"{highlight(text)}</div>",
        unsafe_allow_html=True,
    )


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


def question_card(item, show_answer: bool, number=None):
    """질문 1개 표시. show_answer=False면 답변을 접어둔다. number가 있으면 보조 번호 표시."""
    badge = company_badge(item["company"])
    cat = item.get("category", "")
    title = item.get("title", "")
    st.markdown(
        f"{badge} &nbsp; <span style='color:#888;font-size:0.8rem;'>{cat}"
        + (f" · {item['tag']}" if item.get("tag") else "")
        + "</span>",
        unsafe_allow_html=True,
    )
    if title:
        st.markdown(f"**🔹 {title}**")
    st.markdown(item["question"])
    if show_answer:
        render_answer(item["answer"])
        if item.get("link"):
            st.info("🔗 " + item["link"])
    else:
        with st.expander("💡 모범답변 보기"):
            render_answer(item["answer"])
            if item.get("link"):
                st.info("🔗 " + item["link"])


# ---------------------------------------------------------------- 데이터 로드
data = load_data(DATA_PATH.stat().st_mtime)
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
    st.divider()

    for idx, item in enumerate(filtered, start=1):
        qid = item["id"]
        left, right = st.columns([1, 1])

        # --- 왼쪽: 질문 + 모범답변 ---
        with left:
            badge = company_badge(item["company"])
            cat = item.get("category", "")
            title = item.get("title", "")
            st.markdown(
                f"{badge} &nbsp; "
                f"<span style='color:#888;font-size:0.8rem;'>{cat}"
                + (f" · {item['tag']}" if item.get("tag") else "")
                + "</span>",
                unsafe_allow_html=True,
            )
            # 제목에 번호(6., 6.1. 등)나 (추가 질문) 구분이 들어있으면 함께 표시
            if title:
                st.markdown(f"**🔹 {title}**")
            st.markdown(item["question"])
            with st.expander("💡 모범답변 보기"):
                render_answer(item["answer"])
                if item.get("link"):
                    st.info("🔗 " + item["link"])

        # --- 오른쪽: 내 답변 작성 ---
        with right:
            st.markdown("**✍️ 내 답변**")
            # text_area의 key가 입력 내용을 세션 동안 자동 유지 (저장 버튼 불필요)
            st.text_area(
                "내 답변 작성",
                key=f"draft_{qid}",
                height=160,
                label_visibility="collapsed",
                placeholder="여기에 내 답변을 작성해보세요…",
            )

            # --- 음성 녹음 (실전 연습) ---
            if "my_recordings" not in st.session_state:
                st.session_state.my_recordings = {}

            st.markdown("**🎙️ 실전 연습 녹음**")
            if _MIC_AVAILABLE:
                rec = mic_recorder(
                    start_prompt="🎤 실전 연습 녹음 시작",
                    stop_prompt="⏹️ 녹음 중지",
                    just_once=False,
                    use_container_width=True,
                    format="webm",
                    key=f"mic_{qid}",
                )
                # 새 녹음이 들어오면 질문 id별로 저장
                if rec and rec.get("bytes"):
                    st.session_state.my_recordings[str(qid)] = rec["bytes"]

                saved_audio = st.session_state.my_recordings.get(str(qid))
                if saved_audio:
                    st.audio(saved_audio, format="audio/webm")
                    if st.button("🗑️ 녹음 삭제", key=f"delrec_{qid}"):
                        st.session_state.my_recordings.pop(str(qid), None)
                        st.rerun()
            else:
                st.caption("⚠️ 녹음 기능을 쓰려면 streamlit-mic-recorder 설치가 필요합니다.")

        st.divider()

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
    for idx, item in enumerate(pool, start=1):
        is_done = item["id"] in st.session_state.memorized
        question_card(item, show_answer=False, number=idx)
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
