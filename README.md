(이 저장소의 README는 기본 설명과 로컬 실행 안내를 포함합니다.)

로컬 실행 안내
----------------

이 프로젝트는 Streamlit으로 실행되는 간단한 데모 앱입니다. 주요 기능:

- 챗봇: Azure OpenAI(또는 호환 가능한 모델)를 사용한 스트리밍 챗봇
- RAG: Azure AI Search에서 벡터(또는 텍스트) 검색으로 관련 문서를 찾아 챗봇에 컨텍스트로 제공

필수 환경 변수 (.env)
----------------------

다음 환경 변수를 설정해야 합니다 (예: .env 파일):

- AZURE_SEARCH_ENDPOINT: Azure Search 서비스 엔드포인트 (예: https://<name>.search.windows.net)
- AZURE_SEARCH_API_KEY 또는 AZURE_SEARCH_KEY: Azure Search API 키
- AZURE_SEARCH_INDEX_NAME: 사용할 인덱스 이름
- AZURE_ENDPOINT: Azure OpenAI 엔드포인트 (임베딩/챗 모델 사용 시)
- OPENAI_API_KEY 또는 AZURE_OPENAI_KEY: Azure OpenAI 인증 키
- AZURE_OPENAI_VERSION: Azure OpenAI API 버전 (예: 2024-06-01-preview)
- AZURE_EMBEDDING_DEPLOYMENT: 임베딩 모델(배포 이름), 있으면 벡터 검색을 사용
- AZURE_CHAT_DEPLOYMENT: 챗 모델 배포 이름(기본값: gpt-4.1-mini)

간단 실행 방법
----------------

1. 필요한 패키지 설치:

```powershell
python -m pip install -r requirements.txt
```

2. .env 파일을 프로젝트 루트에 준비

3. Streamlit 앱 실행:

```powershell
python -m streamlit run ktds-msai-6th-mvp\app.py
```

검증 및 문제해결
-----------------

- Azure Search 관련 오류가 발생하면 .env의 인덱스 이름에 따옴표가 포함되어 있지 않은지 확인하세요.
- 벡터 검색을 사용하려면 `AZURE_EMBEDDING_DEPLOYMENT`와 Azure OpenAI 접근이 필요하며, 임베딩을 생성할 수 있는 권한이 있어야 합니다.
- 패키지 설치가 실패하면 `requirements.txt`의 항목을 확인하고 개별적으로 설치해 보세요.

더 필요한 문서나 자동화(예: 인덱스 생성 스크립트)를 원하시면 알려주세요.

