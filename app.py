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

# ---------------------------------------------------------------- 전역 스타일
st.markdown(
    """
    <style>
      /* 본문 폭 살짝 여유 + 상단 여백 줄이기 */
      .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1100px; }

      /* expander(회사정보/STAR/모범답변) 부드러운 카드 느낌 */
      div[data-testid="stExpander"] {
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          box-shadow: 0 1px 2px rgba(0,0,0,0.03);
      }

      /* 라디오(모드 선택) 버튼을 알약 형태로 */
      div[role="radiogroup"] { gap: 8px; }
      div[role="radiogroup"] label {
          background: #f8fafc;
          border: 1px solid #e5e7eb;
          border-radius: 20px;
          padding: 6px 16px;
          transition: all .15s;
      }
      div[role="radiogroup"] label:hover { border-color: #93c5fd; background: #eff6ff; }

      /* 입력창/텍스트영역 라운드 */
      textarea, input[type="text"] { border-radius: 8px !important; }

      /* 버튼 라운드 + 살짝 강조 */
      .stButton button {
          border-radius: 8px;
          font-weight: 600;
      }

      /* 구분선 여백 축소 */
      hr { margin: 0.8rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
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
    "PO 역할", "PO", "피처 엔지니어링", "코호트 분석", "퍼널 분석",
    "데이터 품질", "전처리", "노이즈", "user_id",
    # 역량/태도
    "책임감", "지속적인 성장", "성과를 분석하고 리뷰", "문제를 정의하고 해결",
    "책임의 범위", "업무의 주도성", "데이터 분석과 추출", "리드", "책임",
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


def priority_badge(priority: str) -> str:
    """우선순위 뱃지 HTML. 없으면 빈 문자열."""
    styles = {
        "essential": ("⭐ 1차 필수", "#dc2626"),
        "important": ("🔸 자주 나옴", "#d97706"),
    }
    if priority not in styles:
        return ""
    label, color = styles[priority]
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:12px;font-size:0.8rem;font-weight:700;'>{label}</span> "
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
    prio = priority_badge(item.get("priority", ""))
    cat = item.get("category", "")
    title = item.get("title", "")
    st.markdown(
        f"{prio}{badge} &nbsp; <span style='color:#888;font-size:0.8rem;'>{cat}"
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

# 키워드 힌트(논리 뼈대) 로드 — id(문자열) -> [힌트 줄들]
HINTS_PATH = Path(__file__).resolve().parent / "hints.json"
hints = {}
if HINTS_PATH.exists():
    hints = {k: v for k, v in json.loads(HINTS_PATH.read_text(encoding="utf-8")).items()
             if not k.startswith("_")}

st.markdown(
    "<div style='display:flex;align-items:baseline;gap:10px;'>"
    "<span style='font-size:1.6rem;font-weight:800;'>📒 Study Notes</span>"
    f"<span style='color:#94a3b8;font-size:0.85rem;'>총 {len(data)}개 항목 · {' / '.join(companies)}</span>"
    "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- 회사 정보 섹션
COMPANY_PATH = Path(__file__).resolve().parent / "company_info.json"
if COMPANY_PATH.exists():
    company = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    with st.expander(f"🏢 {company.get('name', '회사 정보')}", expanded=False):
        if company.get("slogan"):
            st.markdown(
                "<div style='border-left:4px solid #2563eb;background:#eff6ff;"
                "padding:10px 14px;border-radius:6px;font-style:italic;'>"
                f"“{company['slogan']}”</div>",
                unsafe_allow_html=True,
            )
            st.write("")
        for f in company.get("fields", []):
            val = f["value"]
            if str(val).startswith("http"):
                val = f"[{val}]({val})"
            st.markdown(f"**{f['label']}** · {val}")
        # 본문 블록들 (제목/내용 쌍) — 순서대로 표시
        for t_key, c_key in [
            ("intro_title", "intro"),
            ("vision_title", "vision"),
            ("requirements_title", "requirements"),
            ("hard_skills_title", "hard_skills"),
            ("soft_skills_title", "soft_skills"),
        ]:
            if company.get(t_key):
                st.markdown(f"#### {company[t_key]}")
                st.markdown(company.get(c_key, ""))
        # 지원동기 — 키워드 하이라이트 적용
        if company.get("motivation_title"):
            st.markdown(f"#### {company['motivation_title']}")
            render_answer(company.get("motivation", ""))

# ---------------------------------------------------------------- STAR 기법 안내
with st.expander("⭐ STAR 기법이란?", expanded=False):
    st.markdown(
        "경험·강점 답변을 **구체적이고 설득력 있게** 말하는 4단계 구조입니다.\n\n"
        "| 글자 | 의미 | 내용 |\n"
        "|---|---|---|\n"
        "| **S** | Situation (상황) | 어떤 상황·배경이었는지 |\n"
        "| **T** | Task (과제·목표) | 해결해야 했던 문제나 목표 |\n"
        "| **A** | Action (행동) | 그래서 내가 한 구체적 행동 |\n"
        "| **R** | Result (결과) | 그 행동으로 만든 성과·결과 |\n\n"
        "💡 실제 면접에서는 'S·T·A·R' 글자를 말하지 말고 **순서대로 자연스럽게** 이야기하세요."
    )

# ---------------------------------------------------------------- 면접 기본 질문 가이드
GUIDE_PATH = Path(__file__).resolve().parent / "basic_guide.json"
if GUIDE_PATH.exists():
    guide = json.loads(GUIDE_PATH.read_text(encoding="utf-8"))
    with st.expander(f"💬 {guide.get('name', '면접 기본 질문 가이드')}", expanded=False):
        if guide.get("tip"):
            st.info("💡 " + guide["tip"])
        for it in guide.get("items", []):
            st.markdown(f"**{it['q']}**")
            if it.get("template"):
                st.caption("📋 템플릿: " + it["template"])
            render_answer(it["answer"])
            st.write("")

mode = st.radio(
    "모드 선택",
    ["📚 회사별 정리", "🧠 암기 모드", "🎲 랜덤 연습", "🎤 말하기 연습"],
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

    # 주제(topic) 필터 — 자료에 있는 주제를 정해진 순서로 노출
    TOPIC_ORDER = [
        "나에 대한 질문", "기술·프로젝트", "일하는 방식", "커뮤니케이션",
        "면접 마무리", "프로젝트 1", "프로젝트 2", "프로젝트 3",
    ]
    present = {d.get("topic", "") for d in filtered}
    topics = [t for t in TOPIC_ORDER if t in present] + \
             sorted(present - set(TOPIC_ORDER) - {""})
    with col2:
        sel_topic = st.selectbox("주제", ["전체"] + topics)
    if sel_topic != "전체":
        filtered = [d for d in filtered if d.get("topic") == sel_topic]

    keyword = st.text_input("🔍 검색 (질문·답변 내 키워드)", placeholder="예: KPI, SQL, 이탈")
    if keyword:
        k = keyword.lower()
        filtered = [
            d for d in filtered
            if k in d["question"].lower() or k in d["answer"].lower()
        ]

    only_essential = st.checkbox("⭐ 1차 필수 질문만 보기")
    if only_essential:
        filtered = [d for d in filtered if d.get("priority") == "essential"]

    st.caption(f"{len(filtered)}개 질문")
    st.divider()

    for idx, item in enumerate(filtered, start=1):
        qid = item["id"]
        left, right = st.columns([1, 1])

        # --- 왼쪽: 질문 + 모범답변 ---
        with left:
            badge = company_badge(item["company"])
            prio = priority_badge(item.get("priority", ""))
            topic = item.get("topic", "")
            title = item.get("title", "")
            meta = topic
            if item.get("tag"):
                meta += f" · {item['tag']}"
            st.markdown(
                f"{prio}{badge} &nbsp; "
                f"<span style='color:#888;font-size:0.8rem;'>{meta}</span>",
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

# ================================================================ 4. 말하기 연습
elif mode == "🎤 말하기 연습":
    st.caption("💡 통암기 대신 **키워드 힌트(뼈대)**만 보고 소리 내어 말해보세요. "
               "막히면 다음 힌트로 넘어가면 됩니다.")

    # 힌트가 있는 질문만 대상으로 (연습 효과 큰 핵심 답변)
    hinted = [d for d in data if str(d["id"]) in hints]
    if not hinted:
        st.warning("아직 키워드 힌트가 준비된 질문이 없습니다.")
    else:
        titles = [f"{d['title']}" for d in hinted]
        sel = st.selectbox("연습할 질문", titles, key="speak_sel")
        item = hinted[titles.index(sel)]

        st.divider()
        # 질문
        prio = priority_badge(item.get("priority", ""))
        st.markdown(f"{prio}**🔹 {item['title']}**", unsafe_allow_html=True)
        st.markdown(f"**Q. {item['question']}**")

        # 키워드 힌트 (항상 표시)
        st.markdown("##### 🎯 키워드 힌트")
        hint_html = "<div style='background:#fffbeb;border:1px solid #fde68a;" \
                    "border-radius:8px;padding:12px 16px;line-height:2;'>"
        for i, line in enumerate(hints[str(item["id"])], 1):
            hint_html += f"<div><b>{i}.</b> {line}</div>"
        hint_html += "</div>"
        st.markdown(hint_html, unsafe_allow_html=True)

        # 음성 녹음 (실전처럼 말해보고 들어보기)
        st.markdown("##### 🎙️ 녹음해서 들어보기")
        if "speak_rec" not in st.session_state:
            st.session_state.speak_rec = {}
        rid = str(item["id"])
        if _MIC_AVAILABLE:
            rec = mic_recorder(
                start_prompt="🎤 녹음 시작", stop_prompt="⏹️ 녹음 중지",
                just_once=False, use_container_width=True,
                format="webm", key=f"speakmic_{rid}",
            )
            if rec and rec.get("bytes"):
                st.session_state.speak_rec[rid] = rec["bytes"]
            if st.session_state.speak_rec.get(rid):
                st.audio(st.session_state.speak_rec[rid], format="audio/webm")
        else:
            st.caption("⚠️ 녹음 기능은 streamlit-mic-recorder 설치 시 사용 가능합니다.")

        # 전체 답변 (접기) — 말한 뒤 비교용
        with st.expander("✅ 전체 모범답변 보기 (말한 뒤 비교)"):
            render_answer(item["answer"])

st.divider()
st.caption("자료 수정: .md 편집 후 parse_md.py 재실행")
