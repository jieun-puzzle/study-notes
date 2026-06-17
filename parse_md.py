"""
면접 준비 .md 파일들을 파싱해 questions.json 으로 변환하는 스크립트.

사용법:
    python parse_md.py

상위 폴더의 `면접준비_*.md` 파일들을 읽어
같은 폴더에 questions.json 을 생성한다.

새 면접 자료가 생기면 .md 파일을 추가하고 이 스크립트를 다시 실행하면 된다.
"""

import json
import re
from pathlib import Path

# 이 스크립트 기준으로 상위 폴더(원본 .md 들이 있는 곳)
BASE_DIR = Path(__file__).resolve().parent.parent
OUT_PATH = Path(__file__).resolve().parent / "questions.json"

# 파싱 대상 파일과 사람이 읽기 좋은 라벨(회사/구분)
# (파일명 패턴, 회사, 카테고리)
SOURCE_FILES = [
    ("6_18.md", "엑셀리언트", "실제 면접 기록"),
    ("면접준비_프로젝트1_압토솔.md", "압토솔", "프로젝트 1"),
    ("면접준비_프로젝트1_올라핀테크.md", "올라핀테크", "프로젝트 1"),
    ("면접준비_프로젝트2_올라핀테크.md", "올라핀테크", "프로젝트 2"),
    ("면접준비_프로젝트3_올라핀테크.md", "올라핀테크", "프로젝트 3"),
]

# 개인정보 보호: 아래 키워드가 제목/질문에 들어간 항목은
# 질문은 그대로 두되 답변(실제 수치·주소·가족 등)을 마스킹한다.
SENSITIVE_KEYWORDS = [
    "연봉",
    "거주지",
    "통근",
    "거주",
]

# 답변 대신 표시할 안내 문구
MASKED_ANSWER = "🔒 개인정보가 포함된 답변이라 비공개 처리했습니다. (실제 답변은 원본 자료 참고)"

# 질문은 남기되, 질문 안의 구체적 개인정보(수치·지명·가족)는 가린다.
# (찾을 패턴, 바꿀 문구)
QUESTION_REDACTIONS = [
    (r"\d{3,4}\s*만\s*원", "○○○만 원"),          # 금액(연봉 등)
    (r"\d{4}년생", "○○년생"),                      # 출생연도
    (r"[가-힣]+동에", "○○동에"),                   # 거주 동(洞)
    (r"[가-힣]+동에서", "○○동에서"),
    (r"형제가 어떻게 되세요\?.*$", "(가족 관련 질문)"),  # 가족 관련 뒷부분
]


def is_sensitive(title: str, question: str) -> bool:
    blob = f"{title} {question}"
    return any(kw in blob for kw in SENSITIVE_KEYWORDS)


def redact_question(question: str) -> str:
    """질문에 남은 구체적 개인정보를 가린다."""
    for pat, repl in QUESTION_REDACTIONS:
        question = re.sub(pat, repl, question)
    return question


def clean(text: str) -> str:
    """마크다운 강조/공백 정리."""
    text = text.strip()
    # 끝/앞쪽 ** 제거
    text = re.sub(r"\*\*", "", text)
    return text.strip()


def parse_interview_format(text: str):
    """
    실제 면접 기록 포맷:
        ## Q1. 제목 **(임원)** `[03:43]`
        **Q (홍지호)**: ...
        **A (송지은)**: ...
    섹션(##) 단위로 끊고, 그 안의 Q/A 를 한 카드로 묶는다.
    """
    cards = []
    # ## 로 시작하는 블록 단위로 분리
    blocks = re.split(r"\n(?=## )", text)
    for block in blocks:
        header_match = re.match(r"##\s+(.+)", block)
        if not header_match:
            continue
        header = header_match.group(1)
        # 태그(임원/기술 등) 추출
        tag_match = re.search(r"\((임원[^)]*|기술[^)]*|[^)]*면접관[^)]*|[^)]*성향[^)]*|Q&A[^)]*)\)", header)
        tag = tag_match.group(1) if tag_match else ""
        # 헤더에서 제목만 (강조/태그/타임코드 제거)
        title = re.sub(r"\*\*\([^)]*\)\*\*", "", header)
        title = re.sub(r"`\[[^\]]*\]`", "", title)
        title = clean(title)

        # 종합/마치며 같은 비 Q&A 섹션은 스킵
        if not re.match(r"Q\d", title) and "Q" not in header[:4]:
            # 질문 마커가 없는 섹션은 건너뜀
            if "**Q" not in block:
                continue

        # Q / A 추출 (여러 Q가 한 블록에 있을 수 있음 -> 묶어서 본문으로)
        q_parts = re.findall(r"\*\*Q[^*]*\*\*\s*:?\s*(.+?)(?=\n\n|\n\*\*A|\Z)", block, re.S)
        a_parts = re.findall(r"\*\*A[^*]*\*\*\s*:?\s*(.+?)(?=\n\n---|\n## |\n\*\*Q|\Z)", block, re.S)

        question = clean(" ".join(q_parts)) if q_parts else ""
        answer = "\n\n".join(clean(a) for a in a_parts).strip() if a_parts else ""

        if not question and not answer:
            continue

        cards.append({
            "title": title,
            "tag": tag,
            "question": question,
            "answer": answer,
        })
    return cards


def parse_project_format(text: str):
    """
    프로젝트 포맷:
        ## 🔍 1. 섹션명
        **Q. 질문...**  (또는 **Q1. 질문...**)
        A. 답변...
        > **[올라핀테크 연결]** ...
    """
    cards = []
    current_section = ""
    # 섹션 헤더 추적을 위해 줄 단위로 본문을 Q 단위 블록으로 분리
    # 먼저 ## 섹션으로 큰 덩어리를 나눔
    section_blocks = re.split(r"\n(?=## )", text)
    for sblock in section_blocks:
        sec_match = re.match(r"##\s+(.+)", sblock)
        if sec_match:
            current_section = clean(re.sub(r"[🔍🛠️🧹📊🤝📈⚙️🤖🚀⚠️💡]", "", sec_match.group(1)))

        # 이 섹션 안에서 **Q...** 단위로 분리
        q_blocks = re.split(r"\n(?=\*\*Q)", sblock)
        for qb in q_blocks:
            qm = re.match(r"\*\*(Q[^*]*)\*\*", qb)
            if not qm:
                continue
            question = clean(qm.group(1))
            # 앞쪽 "Q.", "Q1.", "Q15." 같은 번호 마커 제거
            question = re.sub(r"^Q\d*\.\s*", "", question)
            question = re.sub(r"^\[핵심[^\]]*\]\s*", "", question).strip()
            # 질문 번호(Q1. 등) 제거한 제목용
            # 답변: A. 로 시작하는 부분부터 다음 Q/구분선까지
            am = re.search(r"\nA\.\s*(.+?)(?=\n\*\*Q|\n## |\Z)", qb, re.S)
            answer = clean(am.group(1)) if am else ""
            # 연결 포인트(인용구) 추출
            link = re.search(r">\s*\*\*\[([^\]]+)\]\*\*\s*(.+)", qb)
            link_text = ""
            if link:
                link_text = clean(f"[{link.group(1)}] {link.group(2)}")

            if not question:
                continue
            cards.append({
                "title": current_section,
                "tag": "",
                "question": question,
                "answer": answer,
                "link": link_text,
            })
    return cards


def main():
    all_cards = []
    qid = 0
    for fname, company, category in SOURCE_FILES:
        fpath = BASE_DIR / fname
        if not fpath.exists():
            print(f"[skip] 파일 없음: {fname}")
            continue
        text = fpath.read_text(encoding="utf-8")

        if "실제 면접" in category:
            cards = parse_interview_format(text)
        else:
            cards = parse_project_format(text)

        masked = 0
        for c in cards:
            qid += 1
            c["id"] = qid
            c["company"] = company
            c["category"] = category
            c["source"] = fname
            # 민감 항목: 질문은 유지(구체 정보는 가림), 답변/연결포인트는 마스킹
            if is_sensitive(c.get("title", ""), c.get("question", "")):
                c["question"] = redact_question(c.get("question", ""))
                c["answer"] = MASKED_ANSWER
                if c.get("link"):
                    c["link"] = ""
                masked += 1
            all_cards.append(c)
        note = f" (민감 답변 {masked}개 마스킹)" if masked else ""
        print(f"[ok] {fname}: {len(cards)}개 질문 추출{note}")

    OUT_PATH.write_text(
        json.dumps(all_cards, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n총 {len(all_cards)}개 질문 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
