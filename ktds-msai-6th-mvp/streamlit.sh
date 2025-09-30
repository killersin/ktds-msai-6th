#!/bin/bash
# 설치할 패키지 (개별 설치로 일부 패키지 실패 시 전체 중단 방지)
# python 인터프리터가 명확하도록 python3 -m pip 사용
PY=python3

# pip 업그레이드 (실패해도 계속)
$PY -m pip install --upgrade pip || true

packages=(
	streamlit
	python-dotenv
	langchain
	langchain_openai
	beautifulsoup4
	requests
	pandas
	azure-search-documents
	azure-storage-blob
	opencensus
	opencensus-ext-azure
	opencensus-ext-requests
	opencensus-ext-logging
	Pillow
)

for pkg in "${packages[@]}"; do
	echo "Installing $pkg"
	$PY -m pip install "$pkg" || echo "WARN: failed to install $pkg"
done

# exec로 대체하여 쉘이 아닌 python 프로세스가 PID 1이 되게 함 -> 신호 전달 신뢰도 향상
exec $PY -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0