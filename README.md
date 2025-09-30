# 📘 RAG 기반 KT 컴플라이언스 챗봇

## 📝 프로젝트 개요
**RAG 기반으로 KT 사내 규정 컴플라이언스 질의응답을 지원하고, 최신 뉴스 및 사례를 요약해 알림을 제공하는 AI 어시스턴트**입니다.

> **컴플라이언스(Compliance)**: 기업 내에서 발생할 수 있는 윤리적, 법적, 재무적 리스크를 사전에 방지하고, 관련 규정을 준수하도록 돕는 활동입니다.


## ❗ 문제 정의
1. **복잡하고 방대한 사내 컴플라이언스 규정**으로 인해  
   → 직원들이 필요한 정보를 빠르게 찾고 이해하기 어려움  

2. **컴플라이언스 관련 최신 동향 및 사례 인식 부족**  
   → 지속적인 트렌드 파악이 어렵고, 규정에 대한 인식 수준이 낮음


## ✅ 해결 방안

### 1. RAG 기반 컴플라이언스 챗봇 도입
- 사내 규정 문서를 RAG(Retrieval-Augmented Generation) 기술로 연결  
- 직원이 자연어로 질문하면, 관련 문서를 검색·요약하여 정확하고 이해하기 쉬운 답변 제공  

# 📘 RAG 기반 KT 컴플라이언스 챗봇

간단한 작업 요약
- 이 문서는 로컬 개발 및 PoC(Proof of Concept) 배포를 위한 README입니다.

프로젝트 개요
---------------
RAG(Retrieval-Augmented Generation) 기반으로 KT 사내 컴플라이언스 관련 문서 및 최신 뉴스·사례를 검색·요약하여
직원 질문에 실시간으로 응답하고, 요약 결과를 슬랙으로 자동 전송하는 AI 어시스턴트입니다.

핵심 정의
- 컴플라이언스: 기업 내 윤리적·법적·재무적 리스크를 사전에 방지하고 규정을 준수하도록 지원하는 활동

문제(Problem Statement)
----------------------
1. 내부 규정이 방대하고 복잡하여 직원이 필요한 정보를 즉시 찾기 어려움
2. 컴플라이언스 관련 최신 동향을 일상적으로 파악하기 어려움 → 내부 인식 제고 필요

해결 접근
-----------
1) RAG 기반 검색·응답
 - Azure AI Search로 관련 문서를 검색하고, 검색 결과를 컨텍스트로 Azure OpenAI(GPT-4.1-mini)에 전달하여
      정확하고 근거 있는 응답을 제공합니다.

2) 뉴스 요약 및 알림
 - 외부/내부 게시글을 수집하여 요약을 생성하고, 결과를 슬랙으로 전송하여 사내 인식 제고에 활용합니다.

시스템 아키텍처 (텍스트 요약)
--------------------------------
사용자(브라우저)
     → Streamlit UI (app.py)
          → RAG 파이프라인 (modules/azure_ai_search.py)
               → Azure AI Search (인덱스/검색)
               → Azure OpenAI (LLM 응답)
          → 결과 스트리밍 출력

뉴스 요약 흐름: 게시글 수집 → 요약 생성 → 슬랙 전송 (modules/newssummary.py)

주요 기술 스택
----------------
- 프레임워크: LangChain
- 웹 UI: Streamlit
- 프로그래밍 언어: Python 3.11
- 클라우드: Microsoft Azure (AI Search, OpenAI, App Service, Blob Storage)

RAG 검색 시나리오 예시
-----------------------
- "임직원 보안수준진단사이트 주소 알려줘" → 관련 문서 내 링크/참고 제공
- "컴플라이언스 9가지 분야 뭐가 있어?" → 9대 분야 목록 및 간단 설명 반환
- "점심메뉴 추천" → 업무 범위를 벗어난 요청은 거부 및 가이드 안내

프로젝트 실제 파일 구조 (이 저장소의 `ktds-msai-6th-mvp` 폴더 기준)
---------------------------------------------
```
.deployment                 # 배포 관련(옵션)
.env                       # 환경변수 (개인/비공개 - Git 제외)
app.py                     # Streamlit 앱 엔트리 포인트
streamlit.sh               # 배포/실행 스크립트(예: App Service용)
assets/                    # 정적 자원(추가 가능한 다이어그램 등)
data/
     ├─ board_data.json       # 게시글(뉴스) 예시 데이터
     ├─ 9_field.json          # 컴플라이언스 카테고리 샘플
     └─ uploads/              # 업로드된 파일 임시 저장소
modules/
     ├─ appinsight.py         # App Insights 초기화 및 로깅
     ├─ appinsigjt.py         # (중복/임시) App Insights 관련 파일
     ├─ azure_ai_search.py    # Azure Search 클라이언트 및 인덱싱 유틸
     └─ newssummary.py        # 게시판 목록/상세, 요약 및 슬랙 전송
```

설치 및 실행(개발환경, PowerShell 예시)
------------------------------------
1. 가상환경 생성 및 활성화 (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. 의존성 설치
```powershell
pip install -r requirements.txt
```

3. 환경변수 설정
- 루트 또는 `ktds-msai-6th-mvp` 폴더에 `.env` 파일을 두거나, 운영환경(App Service)의 App Settings에 값을 설정하세요.

권장 환경변수 (예시)
```
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_API_KEY=
AZURE_SEARCH_INDEX_NAME=
AZURE_ENDPOINT=
OPENAI_API_KEY=
AZURE_OPENAI_VERSION=
AZURE_EMBEDDING_DEPLOYMENT=
AZURE_STORAGE_CONNECTION_STRING=
SLACK_WEBHOOK_URL=
APPLICATIONINSIGHTS_CONNECTION_STRING=
```

4. 앱 실행
```powershell
streamlit run app.py
```

운영/배포 팁
-------------
- App Service로 배포 시 의존성은 `requirements.txt`에 명시하고, 환경변수는 포털의 App Settings에 설정하세요.
- 코드 변경 후 서비스가 자동으로 반영되지 않으면 앱 재시작이 필요할 수 있습니다.
- 로그 및 모니터링: Application Insights를 통해 예외/사용성 지표를 수집하세요.

개발 시 주의사항
----------------
- 민감한 키나 시크릿은 `.env`에만 보관하고, 저장소에 커밋하지 마세요.
- 테스트용 데이터는 `data/` 폴더에 보관하되, 실제 서비스 전 검증을 권장합니다.

테스트/사용 예시
-----------------
1. 사이드바에서 "게시글 보기" 선택 → 게시글 목록 확인
2. 각 게시글의 "요약" 버튼으로 요약 생성 → 요약 결과를 슬랙으로 전송
3. 챗봇 모드에서 RAG 질의 수행

기여 및 라이선스
-----------------
- 내부 PoC용 코드입니다. 외부 배포 전 보안·컴플라이언스 검토가 필요합니다.
- 개선 제안이나 이슈는 Pull Request 또는 Issue로 남겨 주세요.

문의
-----
프로젝트 관련 문의는 이슈로 남겨 주시거나, 내부 담당자에게 연락해 주세요.


