import os
import streamlit as st
import json
from dotenv import load_dotenv

load_dotenv()

if "show_board" not in st.session_state:
    st.session_state["show_board"] = False

# 사이드바에 홈으로 버튼 추가
if st.sidebar.button("홈으로"):
    st.session_state["show_board"] = False

# 게시글 보기 버튼
if st.sidebar.button("게시글 보기"):
    st.session_state["show_board"] = True

if st.session_state["show_board"]:
    # st.title, st.caption 숨김, 게시글 테이블만 표시
    json_path = os.path.join("data", "board_data.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            board_list = json.load(f)
        if isinstance(board_list, list) and len(board_list) > 0:
            import pandas as pd
            df = pd.DataFrame([
                {
                    "번호": post.get("postid", ""),
                    "제목": post.get("title", ""),
                    "작성자": post.get("username", ""),
                    "부서": post.get("detptname", ""),
                    "날짜": post.get("createdate", "")
                }
                for post in board_list
            ])
            selected_post_idx = st.session_state.get("selected_post_idx", None)
            if selected_post_idx is None:
                # 표 헤더 표시
                header = st.columns([1, 3, 2, 2, 2])
                header[0].markdown("**번호**")
                header[1].markdown("**제목**")
                header[2].markdown("**작성자**")
                header[3].markdown("**부서**")
                header[4].markdown("**날짜**")

                # 표 행 표시
                for idx, post in enumerate(board_list):
                    cols = st.columns([1, 3, 2, 2, 2])
                    cols[0].write(post.get("postid", ""))
                    if cols[1].button(post.get("title", ""), key=f"title_btn_{idx}"):
                        st.session_state["selected_post_idx"] = idx
                        st.rerun()
                    cols[2].write(post.get("username", ""))
                    cols[3].write(post.get("detptname", ""))
                    cols[4].write(post.get("createdate", ""))
            else:
                # 상세 화면에서도 '게시글 보기' 버튼 표시
                if st.button("목록"):
                    st.session_state["selected_post_idx"] = None
                    st.rerun()
                post = board_list[selected_post_idx]
                with st.container():
                    st.subheader(post.get("title", ""))
                    st.write(f"**번호:** {post.get('postid', '')}")
                    st.write(f"**작성자:** {post.get('username', '')}")
                    st.write(f"**부서:** {post.get('detptname', '')}")
                    st.write(f"**날짜:** {post.get('createdate', '')}")
                    st.markdown(f"---")
                    st.markdown(post.get("message", ""), unsafe_allow_html=True)
        else:
            st.warning("게시글 데이터가 없습니다.")
    except Exception as e:
        st.error(f"게시글을 불러올 수 없습니다: {e}")
else:
    # 챗봇 기본 화면
    st.title("ktds-msai-6th-mvp 🤖 GPT-4o와 대화해보세요!")
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