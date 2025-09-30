#!/bin/bash
# 설치할 패키지
pip install --upgrade pip
pip install streamlit python-dotenv langchain langchain_openai beautifulsoup4 requests pandas azure-search-documents azure-storage-blob azure-ai-openai opencensus opencensus-ext-azure opencensus-ext-requests opencensus-ext-logging Pillow

# 앱 실행
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0