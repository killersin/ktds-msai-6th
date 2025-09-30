## RAG 기반 KT컴플라이언스 챗봇

간단 요약
- 제목: RAG 기반 KT컴플라이언스 챗봇
- 설명: RAG(Retrieval-Augmented Generation) 기반으로 KT 사내 규정 컴플라이언스 질의응답을 지원하고, 최신 뉴스 및 사례를 요약해 알림(슬랙)으로 제공하는 AI 어시스턴트입니다.

프로젝트 목적 및 문제 정의
- 문제 1: 복잡하고 방대한 사내 컴플라이언스 규정 때문에 직원들이 필요한 정보를 빠르게 찾고 이해하기 어려움
- 문제 2: 컴플라이언스 관련 최신 동향과 트렌드를 지속적으로 파악하기 어려워 내부 인식 제고가 필요함

해결 방안
1. RAG 기반 컴플라이언스 챗봇 도입
   - 문서/인덱스(사내 정책, 가이드, FAQ 등)를 검색해 컨텍스트를 생성하고 LLM으로 자연어 응답을 제공합니다.
2. 뉴스 요약 및 슬랙 자동 전송
   - 외부/내부 뉴스 또는 스크랩된 게시글을 주기적으로 요약하고, 요약 결과를 슬랙으로 전송하여 직원들이 쉽게 최신 동향을 파악하도록 지원합니다.

시스템 아키텍처 (텍스트 다이어그램)

클라이언트 (Streamlit Web UI)
  - 사용자는 웹 UI에서 질문 입력, 게시글(뉴스) 열람, 요약 요청, 슬랙 전송을 수행

앱 서버 (Streamlit, Python)
  - 모듈: `app.py` (엔트리), `modules/azure_ai_search.py` (검색/인덱싱), `modules/newssummary.py` (게시판/요약), `modules/appinsight.py` (옵저버빌리티)
  - 기능: 파일 업로드 → Azure Blob(선택) → JSON 자동 인덱싱 → 검색 쿼리 처리 → LLM 호출(RAG)

Azure 서비스
  - Azure AI Search: 문서 인덱싱 및 검색
  - Azure OpenAI: LLM(예: gpt-4.1-mini) — 컨텍스트와 함께 생성
  - App Service (Web App): 배포 대상
  - (선택) Azure Blob Storage: 업로드한 파일 저장

데이터 흐름 요약
  1. 관리자/사용자: 파일 업로드 또는 기존 인덱스 사용
  2. 앱 서버: 업로드된 JSON을 Azure Search로 인덱싱(자동)
  3. 사용자 질문: embedding(선택) 또는 키워드로 검색 → 검색 결과를 컨텍스트로 변환
  4. LLM에 컨텍스트와 질문 전달 → 응답을 스트리밍으로 UI에 표시
  5. 뉴스 요약 기능: 사용자 버튼 또는 스케줄러에서 요약 생성 → 슬랙 전송

기술 스택
- 프레임워크: LangChain
- 웹 UI: Streamlit
- 언어: Python 3.11
- Azure: Azure AI Search, App Service(Web App), (선택) Blob Storage
- LLM: Azure OpenAI (gpt-4.1-mini)

RAG 검색 시나리오 예시
1. 임직원 보안수준진단사이트 주소 알려줘
2. 컴플라이언스 9가지 분야 뭐가 있어?
3. 점심메뉴 추천 — 컴플라이언스 범위 밖의 요청은 거부하도록 구성됨

폴더/주요 파일
- `app.py` — Streamlit 앱 엔트리, 모드 선택, 파일 업로드, 라우팅
- `modules/newssummary.py` — 게시글(뉴스) 목록/상세, 요약 및 슬랙 전송 로직
- `modules/azure_ai_search.py` — Azure Search 클라이언트 래퍼 및 인덱싱 유틸
- `modules/appinsight.py` — Application Insights 로거 초기화(선택)
- `data/board_data.json` — 게시글 예시 데이터
- `requirements.txt` — 의존성 목록

설치 및 실행 (로컬, PowerShell)
1. 가상환경 생성 및 활성화 (권장)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
``` 
2. 의존성 설치
```powershell
pip install -r requirements.txt
```
3. 환경변수 설정
 - 프로젝트 루트 또는 `ktds-msai-6th-mvp` 폴더에 `.env` 파일을 두고 아래 값을 설정하세요.

예시 `.env` (필수/선택):
```
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_API_KEY=...
AZURE_SEARCH_INDEX_NAME=...
AZURE_ENDPOINT=...            # Azure OpenAI 엔드포인트
OPENAI_API_KEY=...            # Azure OpenAI 키
AZURE_OPENAI_VERSION=...      # 예: 2023-05-15
AZURE_EMBEDDING_DEPLOYMENT=...# (선택) 임베딩 모델 이름
AZURE_STORAGE_CONNECTION_STRING=... # (선택) Blob 업로드
SLACK_WEBHOOK_URL=...         # (선택) 요약 전송용
APPLICATIONINSIGHTS_CONNECTION_STRING=... # (선택)
```

4. 앱 실행
```powershell
streamlit run app.py
```

배포
- `streamlit.sh` 스크립트가 포함되어 있어 App Service에서 사용되는 간단한 시작 스크립트를 제공합니다. App Service 배포 시 `requirements.txt`와 `.env` 값을 App Settings로 구성하세요.

테스트 및 사용 예시
- 게시글 보기: 사이드바의 "게시글 보기" 클릭 → 게시글 목록 확인 → 제목 클릭해 상세 확인 → "목록" 버튼으로 돌아오기
- 요약: 게시글 목록에서 "요약" 버튼 클릭 → 요약이 생성되면 "슬랙으로 전송하기"로 전송
- RAG 질문 예시: 위의 시나리오 항목을 입력하여 동작을 확인

문제 해결 팁
- 코드 수정 후 UI가 갱신되지 않으면 브라우저 새로고침 또는 사이드바의 "세션 초기화" 버튼을 눌러 세션을 리셋하세요.
- App Service 배포 후 환경변수는 Azure Portal의 App Settings에 설정해야 합니다.

기여 및 다음 단계
- 인덱스 자동화(스케줄러), 요약 스케줄링(크론), 인증(사내 SSO) 연동, 보다 강력한 권한/접근 제어 추가를 고려하세요.

라이선스
- 내부 PoC 용도로 사용하세요. 추가 배포 전 보안·컴플라이언스 검토 필요.
