import os
import json
import time
import streamlit as st
from dotenv import load_dotenv
import logging
import signal
import atexit

load_dotenv()

# Application Insights 초기화 (modules/appinsight.py에서 제공)
try:
    from modules.appinsight import init_appinsights
    # logger: 모듈 전반에서 사용되는 간단한 로거 인터페이스
    logger = init_appinsights("ktds-msai-mvp")
except Exception:
    logger = None
    # init이 실패하면 기본 로거를 사용하도록 설정
    import logging as _logging
    _logging.getLogger().addHandler(_logging.NullHandler())

# 앱 시작 시 Application Insights에 시작 이벤트 전송 (포털에서 서비스 상태/역할을 빠르게 확인 가능)
if logger:
    try:
        logger.track_event("app_start", {"script": "app.py"})
        logger.info("Application started: ktds-msai-mvp")
    except Exception:
        pass


# 앱 종료 시 Application Insights에 종료 이벤트를 전송하고
# 로거 핸들러들을 flush하여 가능한 한 빨리 원격으로 전송되도록 합니다.
def _flush_appinsights(reason: str = "signal"):
    """앱 종료 시 호출: app_stop 이벤트 전송 및 로거 핸들러 flush (한글 주석)"""
    try:
        # app_stop 이벤트 전송
        if logger:
            try:
                logger.track_event("app_stop", {"script": "app.py", "reason": reason})
                logger.info(f"Application stopping: reason={reason}")
            except Exception:
                # 전송 실패 시 무시
                pass

        # 루트 로거의 핸들러들에 대해 flush()가 있으면 호출
        root = logging.getLogger()
        for h in list(root.handlers):
            try:
                if hasattr(h, "flush"):
                    h.flush()
            except Exception:
                pass
        # 핸들러 flush 후 더 넉넉한 대기 시간을 두어 비동기 전송이 네트워크로 나갈 시간을 줍니다.
        try:
            time.sleep(4)
        except Exception:
            pass
    except Exception:
        # 안전을 위해 예외는 무시
        pass


def _handle_termination(signum, frame):
    """SIGTERM/SIGINT 수신 시 실행되는 핸들러"""
    try:
        # 디버그: 핸들러가 호출되는지 로컬 파일에 기록 (타임스탬프, PID, logger 초기화 상태, 핸들러 수)
        try:
            os.makedirs("data", exist_ok=True)
            pid = os.getpid()
            now = time.strftime('%Y-%m-%dT%H:%M:%S')
            logger_present = bool(logger)
            root = logging.getLogger()
            handler_count = len(list(root.handlers))
            with open(os.path.join("data", "app_shutdown.log"), "a", encoding="utf-8") as fh:
                fh.write(f"{now} _handle_termination called: signum={signum} pid={pid} logger_present={logger_present} handlers={handler_count}\n")
        except Exception:
            pass

        # 가능한 경우 app_stop 전송
        _flush_appinsights(reason=f"signum_{signum}")
    finally:
        # 종료 시 프로세스 종료 호출 (Streamlit 환경에서도 정상 종료를 시도)
        try:
            import sys
            sys.exit(0)
        except Exception:
            pass


# 대부분의 Linux 기반 App Service에서는 SIGTERM이 전달됩니다.
# Windows나 일부 환경에서는 signal 등록이 제한적일 수 있어 예외를 무시합니다.
try:
    signal.signal(signal.SIGTERM, _handle_termination)
    signal.signal(signal.SIGINT, _handle_termination)
except Exception:
    # signal 등록 불가 환경일 수 있음 — 무시
    pass


# 인터프리터 정상 종료 시에도 app_stop을 전송하도록 atexit에 등록
try:
    atexit.register(lambda: _flush_appinsights(reason="atexit"))
except Exception:
    pass


st.set_page_config(page_title="KTDS MSAI MVP 616", page_icon="🛡️")

if "show_board" not in st.session_state:
    st.session_state["show_board"] = False

if st.sidebar.button("홈으로"):
    st.session_state["show_board"] = False
    st.session_state["messages"] = []
if st.sidebar.button("게시글 보기"):
    st.session_state["show_board"] = True
    st.session_state["messages"] = []

# 사이드바: 파일 업로드 (게시글 보기 버튼과 모드 선택 사이)
UPLOAD_DIR = os.path.join("data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

uploaded_files = st.sidebar.file_uploader("파일 업로드 (여러개 가능)", accept_multiple_files=True)
if uploaded_files:
    if "uploaded_files" not in st.session_state:
        st.session_state["uploaded_files"] = []
    for f in uploaded_files:
        # 저장 경로 결정 (중복 방지)
        save_name = f.name
        save_path = os.path.join(UPLOAD_DIR, save_name)
        if os.path.exists(save_path):
            base, ext = os.path.splitext(save_name)
            save_name = f"{base}_{int(time.time())}{ext}"
            save_path = os.path.join(UPLOAD_DIR, save_name)
        try:
            with open(save_path, "wb") as out:
                out.write(f.getbuffer())
            #st.sidebar.success(f"저장 완료: {save_name}")
            if logger:
                try:
                    logger.info(f"File saved: {save_path}")
                except Exception:
                    pass
            meta = {"name": save_name, "path": save_path, "type": f.type, "size": os.path.getsize(save_path)}
            st.session_state["uploaded_files"].append(meta)

            # Azure Blob Storage에 업로드 시도
            conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if conn_str:
                try:
                    from azure.storage.blob import BlobServiceClient
                    blob_service = BlobServiceClient.from_connection_string(conn_str)
                    container_name = "compliance"
                    try:
                        container_client = blob_service.create_container(container_name)
                    except Exception:
                        container_client = blob_service.get_container_client(container_name)

                    blob_client = blob_service.get_blob_client(container=container_name, blob=save_name)
                    with open(save_path, "rb") as data:
                        blob_client.upload_blob(data, overwrite=True)
                    #st.sidebar.success(f"Blob 업로드 성공: {container_name}/{save_name}")
                    meta["blob_url"] = blob_client.url
                    if logger:
                        try:
                            logger.info(f"Blob uploaded: {container_name}/{save_name} -> {meta['blob_url']}")
                        except Exception:
                            pass
                except Exception as e:
                    st.sidebar.error(f"Blob 업로드 실패: {e}")
                    if logger:
                        try:
                            logger.exception(f"Blob upload failed: {save_name}")
                        except Exception:
                            pass
            else:
                st.sidebar.warning("AZURE_STORAGE_CONNECTION_STRING이 설정되어 있지 않아 Blob 업로드를 건너뜁니다.")

            # 자동 인덱싱: 업로드된 파일이 JSON이면 Azure Search 인덱스에 색인 시도
            try:
                if save_path.lower().endswith('.json'):
                    try:
                        from modules.azure_ai_search import AzureSearchClient
                        # 사이드바와 메인에 메시지를 표시할 수 있는 placeholder 사용
                        sidebar_ph = st.sidebar.empty()
                        main_ph = st.empty()

                        sidebar_ph.info("업로드된 JSON을 Azure Search에 인덱싱 중입니다...")
                        if logger:
                            try:
                                logger.info(f"Start indexing file: {save_path}")
                            except Exception:
                                pass
                        asc = AzureSearchClient()
                        asc.ensure_index_exists()
                        res = asc.index_from_file(file_path=save_path)
                        msg = f"인덱싱 완료: 총={res.get('total')}, 성공={res.get('success')}, 실패={res.get('failed')}"

                        # 잠깐 메인에 표시하고 자동으로 제거
                        #main_ph.success(f"파일 인덱싱 성공: {save_name} — {msg}")
                        # 사이드바에도 결과를 잠시 보여줬다가 지움
                        sidebar_ph.success(msg)
                        if logger:
                            try:
                                logger.info(f"Indexing result for {save_name}: {msg}")
                            except Exception:
                                pass
                        time.sleep(3)
                        try:
                            main_ph.empty()
                        except Exception:
                            pass
                        try:
                            sidebar_ph.empty()
                        except Exception:
                            pass
                    except ValueError as ve:
                        # 환경변수 누락으로 초기화 실패 시 사용자에게 안내
                        st.sidebar.warning(f"인덱스 초기화 건너뜀: {ve}")
                        if logger:
                            try:
                                logger.warning(f"Index init skipped: {ve}")
                            except Exception:
                                pass
                    except Exception as ie:
                        st.sidebar.error(f"인덱싱 예외 발생: {ie}")
                        if logger:
                            try:
                                logger.exception(f"Indexing failed for {save_name}: {ie}")
                            except Exception:
                                pass
            except Exception:
                # 안전을 위해 전체 블록의 예외를 무시하고 계속 진행
                pass

        except Exception as e:
            st.sidebar.error(f"파일 저장 실패: {e}")

mode = st.sidebar.selectbox("모드 선택", ["Azure Search", "일반검색"])

# 모드 변경 시 이전 대화 메시지 초기화
if "last_mode" not in st.session_state:
    st.session_state["last_mode"] = mode
elif st.session_state["last_mode"] != mode:
    # 모드가 바뀌면 이전 세션 메시지를 초기화하여 혼동을 방지
    st.session_state["messages"] = []
    st.session_state["last_mode"] = mode

# 게시글 모듈 분리 호출
if st.session_state["show_board"]:
    try:
        from modules.newssummary import show_board
        show_board()
    except Exception as e:
        st.error(f"게시글 모듈을 로드할 수 없습니다: {e}")
    raise SystemExit  # 게시판 화면만 보여주고 종료 (이후 코드는 실행하지 않음)

# --- 유틸리티 함수들 ---
# 환경변수 키를 읽어 딕셔너리로 반환합니다.
# 반환값 예시: {"search_endpoint": "...", "search_key": "...", "search_index": "...", ...}
def _get_env_keys():
    return {
        "search_endpoint": os.getenv("AZURE_SEARCH_ENDPOINT"),
        "search_key": os.getenv("AZURE_SEARCH_API_KEY"),
        "search_index": os.getenv("AZURE_SEARCH_INDEX_NAME"),
        "embedding_deployment": os.getenv("AZURE_EMBEDDING_DEPLOYMENT"),
        "chat_deployment": "gpt-4.1-mini",
        "azure_endpoint": os.getenv("AZURE_ENDPOINT"),
        "openai_key": os.getenv("OPENAI_API_KEY"),
        "openai_version": os.getenv("OPENAI_API_VERSION")
    }

# Azure Search용 SearchClient를 초기화하여 반환합니다.
# 인자: endpoint(검색 서비스 엔드포인트), key(검색 서비스 키), index(인덱스 이름)
# 반환: SearchClient 인스턴스 또는 초기화 실패 시 None
def _init_search_client(endpoint, key, index):
    if not (endpoint and key and index):
        return None
    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
        return SearchClient(endpoint=endpoint, index_name=index, credential=AzureKeyCredential(key))
    except Exception:
        return None

# 주어진 프롬프트에 대해 Azure OpenAI 임베딩을 요청하여 벡터를 반환합니다.
# 인자: prompt(텍스트), deployment(임베딩 모델 이름), env(환경변수 딕셔너리)
# 반환: embedding 벡터(list) 또는 실패 시 None
def _get_embedding(prompt, deployment, env):
    if not deployment:
        return None
    try:
        import importlib
        oa_mod = importlib.import_module("azure.ai.openai")
        OpenAIClient = getattr(oa_mod, "OpenAIClient")
        from azure.core.credentials import AzureKeyCredential as CoreAzureKey
        if not (env["openai_key"] and env["azure_endpoint"]):
            return None
        oa_client = OpenAIClient(env["azure_endpoint"], CoreAzureKey(env["openai_key"]))
        emb_resp = oa_client.embeddings.create(model=deployment, input=prompt)
        return emb_resp.data[0].embedding
    except Exception:
        return None

# Azure Search에서 프롬프트(또는 임베딩)를 사용해 문서를 검색하여 리스트로 반환합니다.
# 인자: search_client, prompt, embedding_vector, top_k
# 반환: 문서 dict 리스트 (id, domain, category, content, score 등)
def _retrieve_documents(search_client, prompt, embedding_vector, top_k):
    docs = []
    if not search_client:
        return docs
    try:
        if embedding_vector is not None:
            try:
                results = search_client.search(search_text="*", vector={"value": embedding_vector, "fields": "content_vector", "k": top_k})
            except TypeError:
                results = search_client.search(search_text="", vector={"value": embedding_vector, "fields": "content_vector", "k": top_k})
        else:
            results = search_client.search(search_text=prompt, top=top_k)

        for r in results:
            docs.append({
                "id": r.get("id") or r.get("@search.documentId"),
                "domain": r.get("domain"),
                "category": r.get("category") or r.get("title") or "",
                "content": r.get("content") or r.get("text") or "",
                "score": r.get("@search.score")
            })
    except Exception as e:
        st.error(f"Azure Search 조회 실패: {e}")
    return docs

def _build_context_text(retrieved_docs):
    """
    검색된 문서 리스트로부터 모델에 주입할 컨텍스트 텍스트를 생성합니다.
    각 문서마다 출처 헤더를 붙여 하나의 문자열로 합쳐 반환합니다.
    """
    if not retrieved_docs:
        return ""
    parts = []
    for i, d in enumerate(retrieved_docs):
        header = f"[출처 {i+1}] "
        if d.get("domain"):
            header += d.get("domain") + " | "
        parts.append(header + d.get("content", ""))
    return "\n\n".join(parts)

def _inject_context_into_messages(messages, context_text):
    """
    기존 메시지 목록에 시스템 컨텍스트 메시지를 삽입하여 반환합니다.
    context_text가 빈 경우 원본 메시지를 그대로 반환합니다.
    """
    if not context_text:
        return messages
    system_context = {
        "role": "system",
        "content": (
            "당신은 주식회사 KT의 컴플라이언스 담당자입니다.\n"
            "사용자들의 컴플라이언스 관련 질의에 답변을 도와주는 helpful assistant입니다.\n"
            "컴플라이언스는 기업활동에서 벌어질 수 있는 법률적, 윤리적, 재무적, 비재무적 위험요소를 사전에 억제하고 방지하는 활동을 의미합니다.\n"
            "확실하지 않거나 답변이 없으면 모른다고 명시하세요.\n\n"
        ) + context_text
    }
    msgs = [m for m in messages]
    insert_pos = max(0, len(msgs) - 1)
    msgs.insert(insert_pos, system_context)
    return msgs

# 모델 스트리밍 응답을 받아 Streamlit 채팅 UI에 실시간으로 출력하고 최종 응답 텍스트를 반환합니다.
# 인자: model(스트리밍 모델 래퍼), messages_for_model(모델에 전달할 메시지 리스트)
# 반환: 모델이 생성한 전체 응답 문자열
def _stream_response_to_chat(model, messages_for_model):
    response_text = ""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            for chunk in model.stream(messages_for_model):
                response_text += chunk.content
                placeholder.markdown(response_text)
        except Exception as e:
            st.error(f"모델 호출 중 오류: {e}")
    return response_text

# LangChain 기반 AzureChatOpenAI 모델을 초기화하여 반환합니다.
# 인자: env(환경변수 딕셔너리), deployment(챗 모델 배포 이름)
# 반환: 모델 인스턴스 또는 실패 시 None
def _init_chat_model(env, deployment):
    try:
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint=env["azure_endpoint"],
            api_key=env["openai_key"],
            api_version=env["openai_version"],
            azure_deployment=deployment
        )
    except Exception as e:
        st.error(f"모델 초기화 실패: {e}")
        return None

# 로컬 JSON에서 카테고리명을 읽어 리스트로 반환합니다.
# 반환값에는 원본 '번호. 이름'과 번호를 제거한 단축명(예: '산업안전보건')을 모두 포함합니다.
def _load_local_categories(path="data/9_field.json"):
    cats = []
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    c = item.get("category")
                    if c:
                        cats.append(c)
                        # 숫자 접두사 제거 (예: '7. 산업안전보건' -> '산업안전보건')
                        short = c
                        if "." in c:
                            short = c.split(".", 1)[1].strip()
                        cats.append(short)
    except Exception:
        # 실패해도 빈 리스트 반환
        return []
    return list(dict.fromkeys([c for c in cats if c]))


def _format_messages_for_slack(messages):
    # 간단한 텍스트로 변환: 역할 구분과 내용
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"[{role.upper()}] {content}")
    return "\n\n".join(parts)


def _send_to_slack(messages):
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    payload_text = _format_messages_for_slack(messages)
    if not webhook:
        st.warning("SLACK_WEBHOOK_URL이 설정되어 있지 않습니다. 환경변수에 Webhook URL을 추가하세요.")
        # 대신 포맷된 내용을 확인할 수 있도록 모달처럼 표기
        st.code(payload_text)
        return
    try:
        import requests
        resp = requests.post(webhook, json={"text": payload_text}, timeout=5)
        if resp.status_code == 200:
            st.success("대화 내용을 Slack으로 전송했습니다.")
        else:
            st.error(f"Slack 전송 실패: {resp.status_code} {resp.text}")
    except Exception as e:
        st.error(f"Slack 전송 중 오류: {e}")


# --- 공통 상태 초기화 ---
if "messages" not in st.session_state:
    # 기본 시스템 메시지 없이 빈 대화 이력으로 시작합니다.
    st.session_state["messages"] = []
if "rag_top_k" not in st.session_state:
    st.session_state["rag_top_k"] = 5

# 화면 렌더링
env = _get_env_keys()

# 로컬 JSON에서 카테고리 목록을 미리 로드
LOCAL_CATEGORIES = _load_local_categories()

if mode == "Azure Search":
    if not (env["search_endpoint"] and env["search_key"] and env["search_index"]):
        st.info("Azure Search 설정이 .env에 없습니다. AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME을 설정하세요.")
    else:
        st.title("😀컴플라이언스 챗봇")
        st.caption("Azure AI Search와 OpenAI GPT-4.1-mini를 활용한 실시간 컴플라이언스 RAG 챗봇입니다.")
        model = _init_chat_model(env, env["chat_deployment"])
        if not model:
            st.error("챗봇 모델을 초기화할 수 없습니다.")
        else:
            # 히스토리 표시
            for msg in st.session_state["messages"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if prompt := st.chat_input("User : "):
                st.session_state["messages"].append({"role": "user", "content": prompt})
                # 사용자의 메시지는 먼저 별도 블록으로 렌더링
                with st.chat_message("user"):
                    st.markdown(prompt)

                # 사용자 블록 종료 후 검색 및 모델 호출 로직을 실행하여
                # assistant 메시지가 별도의 채팅 블록으로 렌더되도록 합니다.
                search_client = _init_search_client(env["search_endpoint"], env["search_key"], env["search_index"])
                embedding_vector = _get_embedding(prompt, env["embedding_deployment"], env)
                top_k = int(st.session_state.get("rag_top_k", 5))
                # 카테고리 개요 요청 판별: 로컬 카테고리 이름이 프롬프트에 포함된 경우
                is_category_overview = any(cat in prompt for cat in LOCAL_CATEGORIES)

                if is_category_overview:
                    # agg 문서(item_index == -1)를 우선 조회하여 카테고리 설명을 확보
                    retrieved_docs = _retrieve_documents(search_client, prompt, embedding_vector, top_k)
                    # 필터링 없이 이미 index에서 agg_doc가 생성되어 있으면 포함되어야 함
                else:
                    retrieved_docs = _retrieve_documents(search_client, prompt, embedding_vector, top_k)

                if not retrieved_docs:
                    canned = "컴플라이언스 관련 문의에 대해서만 답변을 제공하고 있음을 안내드립니다.\n그 외의 문의사항은 답변이 어려운 점 양해 부탁드립니다."
                    st.info(canned)
                    # 모델을 호출하지 않고 고정 응답을 대화 이력에 추가
                    st.session_state["messages"].append({"role": "assistant", "content": canned})
                else:
                    st.subheader(f"검색 결과 ({len(retrieved_docs)})")
                    for d in retrieved_docs:
                        title_parts = [p for p in (d.get("domain"), d.get("category")) if p]
                        title = " | ".join(title_parts) if title_parts else (d.get("category") or "항목")
                        with st.expander(f"{title} — {d.get('score')}"):
                            content = (d.get("content") or "").lstrip()  # 선행 공백 제거
                            st.text(content)  # 또는 st.write(content) / st.markdown(content) 대신 st.text 사용

                    context_text = _build_context_text(retrieved_docs)
                    messages_for_model = _inject_context_into_messages(st.session_state["messages"], context_text)

                    response_text = _stream_response_to_chat(model, messages_for_model)
                    # 모델이 생성한 응답을 세션 이력에 저장하여 다음 질문 시 이전 답변이 유지되게 함
                    try:
                        if response_text:
                            st.session_state.setdefault("messages", []).append({"role": "assistant", "content": response_text})
                    except Exception:
                        # 세션 저장 실패시 앱은 계속 실행
                        pass

                        
else:
    # 챗봇 기본 화면 (RAG 없음)
    st.title("ktds-msai-6th-mvp 🤖")
    st.caption("Azure OpenAI의 최신 GPT-4.1-mini 모델을 사용한 스트리밍 챗봇입니다.")
    model = _init_chat_model(env, "gpt-4.1-mini")
    if not model:
        st.error("챗봇 모델을 초기화할 수 없습니다.")
    else:
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("User : "):
            st.session_state["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            response_text = _stream_response_to_chat(model, st.session_state["messages"])
            # 일반검색(라그 없음)에서도 모델 응답을 세션 이력에 저장
            try:
                if response_text:
                    st.session_state.setdefault("messages", []).append({"role": "assistant", "content": response_text})
            except Exception:
                pass
