import os
import streamlit as st
import json
import requests
import pandas as pd

from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

st.set_page_config(
    page_title="KTDS MSAI MVP 616",
    page_icon="🛡️"  # 또는 ":robot:" 또는 "https://example.com/favicon.png"
)

if "show_board" not in st.session_state:
    st.session_state["show_board"] = False

# 사이드바: 모드 선택(좌측화면 분류)
mode = st.sidebar.selectbox("모드 선택", ["챗봇", "일반검색", "Azure Search"])

# 사이드바에 홈으로/게시글 보기 버튼 추가
if st.sidebar.button("홈으로"):
    st.session_state["show_board"] = False

# 게시글 보기 버튼
if st.sidebar.button("게시글 보기"):
    st.session_state["show_board"] = True

if st.session_state["show_board"]:
    # 게시글 관련 기능을 modules.newssummary로 분리
    try:
        from modules.newssummary import show_board
        show_board()
    except Exception as e:
        st.error(f"게시글 모듈을 로드할 수 없습니다: {e}")
else:
    # 모드에 따라 메인 화면 렌더링
    if mode == "Azure Search":
        # --- Azure Search + RAG 챗봇 ---
        try:
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
            search_key = os.getenv("AZURE_SEARCH_API_KEY") or os.getenv("AZURE_SEARCH_KEY")
            search_index = os.getenv("AZURE_SEARCH_INDEX_NAME") or os.getenv("AZURE_SEARCH_INDEX")
            embedding_deployment = os.getenv("AZURE_EMBEDDING_DEPLOYMENT") or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

            if not (search_endpoint and search_key and search_index):
                st.info("Azure Search 설정이 .env에 없습니다. AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME을 설정하세요.")
            else:
                st.markdown("## RAG 챗봇 (Azure Search)")
                # Chat UI reused
                from langchain_openai import AzureChatOpenAI
                model = AzureChatOpenAI(
                    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                    api_key=os.getenv("OPENAI_API_KEY"),
                    api_version=os.getenv("AZURE_OPENAI_VERSION"),
                    azure_deployment=os.getenv("AZURE_CHAT_DEPLOYMENT") or "gpt-4.1-mini"
                )

                # ensure messages
                if "messages" not in st.session_state:
                    st.session_state["messages"] = [{"role": "system", "content": "You are a helpful assistant."}]

                # show history
                for msg in st.session_state["messages"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                # user input
                if prompt := st.chat_input("User : "):
                    st.session_state["messages"].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    # Prepare Azure Search client
                    credential = AzureKeyCredential(search_key)
                    search_client = SearchClient(endpoint=search_endpoint, index_name=search_index, credential=credential)

                    # Try to compute embedding for the query (Azure OpenAI) for vector search
                    embedding_vector = None
                    if embedding_deployment:
                        try:
                            import importlib
                            oa_mod = importlib.import_module("azure.ai.openai")
                            OpenAIClient = getattr(oa_mod, "OpenAIClient")
                            from azure.core.credentials import AzureKeyCredential as CoreAzureKey
                            oa_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
                            oa_endpoint = os.getenv("AZURE_ENDPOINT")
                            if oa_key and oa_endpoint:
                                oa_client = OpenAIClient(oa_endpoint, CoreAzureKey(oa_key))
                                emb_resp = oa_client.embeddings.create(model=embedding_deployment, input=prompt)
                                embedding_vector = emb_resp.data[0].embedding
                        except Exception:
                            # embedding client not available or failed — fallback to text search
                            embedding_vector = None

                    top_k = int(st.session_state.get("rag_top_k", 5))

                    retrieved_docs = []
                    try:
                        if embedding_vector is not None:
                            # vector search
                            try:
                                results = search_client.search(search_text="*", vector={"value": embedding_vector, "fields": "content_vector", "k": top_k})
                            except TypeError:
                                # older SDK shape
                                results = search_client.search(search_text="", vector={"value": embedding_vector, "fields": "content_vector", "k": top_k})
                        else:
                            # fallback to text search
                            results = search_client.search(search_text=prompt, top=top_k)

                        for r in results:
                            doc = {
                                "id": r.get("id") or r.get("@search.documentId") or None,
                                "category": r.get("category") or r.get("title") or "",
                                "content": r.get("content") or r.get("text") or "",
                                "score": r.get("@search.score")
                            }
                            retrieved_docs.append(doc)
                    except Exception as e:
                        st.error(f"Azure Search 조회 실패: {e}")

                    # Display retrieved docs
                    if retrieved_docs:
                        st.subheader(f"검색 결과 ({len(retrieved_docs)})")
                        for d in retrieved_docs:
                            with st.expander(f"{d.get('category')} — {d.get('score')}"):
                                st.write(d.get("content"))

                    # Build context from retrieved docs and ask model
                    context_text = "\n\n".join([f"[출처 {i+1}] {d.get('content')}" for i, d in enumerate(retrieved_docs)])
                    if context_text:
                        system_context = {
                            "role": "system",
                            "content": "다음은 검색된 문서들입니다. 사용자 질문에 답할 때 이 내용을 참고하세요:\n" + context_text
                        }
                        # construct messages with context injected before the user message
                        messages_for_model = [m for m in st.session_state["messages"]]
                        # insert system_context right before last user message
                        messages_for_model.insert(len(messages_for_model)-1, system_context)
                    else:
                        messages_for_model = st.session_state["messages"]

                    # Call model (stream)
                    response_text = ""
                    with st.chat_message("assistant"):
                        placeholder = st.empty()
                        try:
                            for chunk in model.stream(messages_for_model):
                                response_text += chunk.content
                                placeholder.markdown(response_text)
                        except Exception as e:
                            st.error(f"모델 호출 중 오류: {e}")

                    st.session_state["messages"].append({"role": "assistant", "content": response_text})
        except Exception as e:
            st.error(f"검색 UI 초기화 오류: {e}")

    elif mode == "일반검색":
        # --- 로컬 JSON 기반 단순 검색 ---
        st.markdown("## 로컬 문서 검색")
        q = st.text_input("검색어 (로컬 데이터)", key="local_search_query")
        top_k = st.number_input("최대 결과수", min_value=1, max_value=50, value=10)
        if q:
            # 후보 파일 로드
            candidates = [
                os.path.join("data", "9_field.json"),
                os.path.join("data", "9_domains.json"),
                os.path.join("data", "test.json"),
            ]
            data = None
            for p in candidates:
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            break
                    except Exception:
                        continue

            if data is None:
                st.warning("로컬 데이터 파일을 찾을 수 없습니다. data/*.json 파일을 확인하세요.")
            else:
                # 문서 리스트 생성
                docs = []
                if isinstance(data, dict):
                    for cat, items in data.items():
                        for idx, item in enumerate(items):
                            docs.append({"id": f"{cat}-{idx}", "category": cat, "content": item})
                elif isinstance(data, list):
                    for idx, item in enumerate(data):
                        if isinstance(item, dict):
                            docs.append({"id": item.get("id") or f"item-{idx}", "category": item.get("category"), "content": item.get("content")})
                        else:
                            docs.append({"id": f"item-{idx}", "category": None, "content": str(item)})

                # 간단한 서브스트링 검색
                ql = q.lower()
                matches = [d for d in docs if d.get("content") and ql in d.get("content").lower()]
                st.subheader(f"{len(matches)}개의 결과")
                for m in matches[:top_k]:
                    with st.expander(f"{m.get('category') or '항목'} — {m.get('id')}"):
                        st.write(m.get("content"))

    else:
        # --- 챗봇 기본 화면 ---
        st.title("ktds-msai-6th-mvp 🤖")
        st.caption("Azure OpenAI의 최신 GPT-4o-mini 모델을 사용한 스트리밍 챗봇입니다.")
        from langchain_openai import AzureChatOpenAI
        model = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_key=os.getenv("OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_VERSION"),
            azure_deployment="gpt-4.1-mini"
        )
        if "messages" not in st.session_state:
            st.session_state["messages"] = [
                {"role": "system", "content": "You are a helpful assistant."}
            ]
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("User : "):
            st.session_state["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            response_text = ""
            with st.chat_message("assistant"):
                placeholder = st.empty()
                for chunk in model.stream(st.session_state["messages"]):
                    response_text += chunk.content
                    placeholder.markdown(response_text)

            st.session_state["messages"].append({"role": "assistant", "content": response_text})