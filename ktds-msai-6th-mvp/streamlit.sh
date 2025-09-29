#!/bin/bash
# 설치할 패키지
pip install --upgrade pip
pip install streamlit python-dotenv langchain_openai beautifulsoup4 requests pandas azure-search-documents

# 인덱스 생성 및 인덱싱 (있으면 스킵 또는 업데이트)
echo "🔁 Azure Search 인덱스 생성 및 데이터 업로드 시도"
python -m modules.azure_ai_search || echo "⚠️ 인덱스 생성/업로드 중 오류 발생 — 계속해서 Streamlit을 실행합니다."

# 앱 실행
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0