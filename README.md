# 🎤 면접 준비 암기 앱 (송지은)

면접 준비 `.md` 자료를 **암기 모드 / 모바일 복습 / 모의 면접 / 회사별 정리**로 활용하는 Streamlit 앱입니다.

## 폴더 구성

```
streamlit_app/
├── app.py            # 앱 본체
├── parse_md.py       # 상위 폴더의 면접준비_*.md → questions.json 변환
├── questions.json    # 파싱된 질문 데이터 (parse_md.py 가 생성)
├── requirements.txt  # 배포용 의존성
└── README.md
```

## 로컬에서 실행

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

브라우저가 자동으로 열립니다. **같은 와이파이라면 핸드폰에서 `Network URL`** (예: `http://172.30.1.81:8501`)로 접속해 모바일 복습도 가능합니다.

## 자료 수정 / 추가

질문 자료는 상위 폴더의 `면접준비_*.md` 파일에서 가져옵니다.

1. `.md` 파일 내용을 수정하거나 새 파일을 추가
2. (새 파일이면) `parse_md.py` 의 `SOURCE_FILES` 리스트에 한 줄 추가
3. 아래 실행 → `questions.json` 갱신

```bash
python parse_md.py
```

## 인터넷에 무료 배포 (Streamlit Community Cloud)

> ⚠️ **주의**: 이 자료에는 실제 면접 내용·연봉·거주지 등 개인정보가 포함되어 있습니다.
> 공개 배포 시 누구나 URL로 볼 수 있으니, **비공개(Private) 저장소 + 비공개 앱**으로 배포하거나
> 민감 정보를 먼저 제거하는 것을 권장합니다.

1. 이 `streamlit_app` 폴더를 GitHub 저장소에 올립니다 (private 권장).
2. <https://share.streamlit.io> 에 GitHub 계정으로 로그인합니다.
3. **New app** → 저장소 / 브랜치 / `app.py` 경로 선택 → Deploy.
4. 몇 분 뒤 `https://<앱이름>.streamlit.app` 주소가 생기고, PC·모바일 어디서나 접속됩니다.

`questions.json` 이 저장소에 함께 올라가 있어야 배포 환경에서도 데이터를 읽을 수 있습니다.
