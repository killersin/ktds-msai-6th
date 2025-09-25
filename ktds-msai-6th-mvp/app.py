import os
import streamlit as st
import json
import requests
import pandas as pd

from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup

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
    from bs4 import BeautifulSoup
    def html_to_slack_text(html):
        soup = BeautifulSoup(html, "html.parser")
        # 링크 변환: <a href="url">text</a> → <url|text>
        for a in soup.find_all('a'):
            url = a.get('href', '')
            text = a.get_text()
            slack_link = f'<{url}|{text}>' if url else text
            a.replace_with(slack_link)
        # 나머지 태그 제거, 텍스트만 반환
        return soup.get_text(separator="\n")
    # st.title, st.caption 숨김, 게시글 테이블만 표시
    json_path = os.path.join("data", "board_data.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            board_list = json.load(f)
        if isinstance(board_list, list) and len(board_list) > 0:
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
                # 표 헤더 표시 (뉴스요약 컬럼 추가)
                header = st.columns([2, 10, 4, 4, 4, 4])
                header[0].markdown("**번호**")
                header[1].markdown("**제목**")
                header[2].markdown("**작성자**")
                header[3].markdown("**부서**")
                header[4].markdown("**날짜**")
                header[5].markdown("**뉴스요약**")

                def format_date(date_str):
                    try:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        return dt.strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        return date_str

                # 요약 결과 저장용 세션 상태 초기화
                if "news_summaries" not in st.session_state:
                    st.session_state["news_summaries"] = {}

                # 표 행 표시
                for idx, post in enumerate(board_list):
                    cols = st.columns([2, 10, 4, 4, 4, 4])
                    cols[0].write(post.get("postid", ""))
                    if cols[1].button(post.get("title", ""), key=f"title_btn_{idx}"):
                        st.session_state["selected_post_idx"] = idx
                        st.rerun()
                    cols[2].write(post.get("username", ""))
                    cols[3].write(post.get("detptname", ""))
                    # 날짜 포맷 변경
                    cols[4].write(format_date(post.get("createdate", "")))
                    # 뉴스요약 버튼
                    if cols[5].button("요약", key=f"summary_btn_{idx}"):
                        # 기존 요약 모두 삭제
                        st.session_state["news_summaries"] = {}
                        # GPT 요약 요청
                        from langchain_openai import AzureChatOpenAI
                        model = AzureChatOpenAI(
                            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                            api_key=os.getenv("OPENAI_API_KEY"),
                            api_version=os.getenv("AZURE_OPENAI_VERSION"),
                            azure_deployment="gpt-4.1-mini"
                        )
                        prompt = (f"다음 뉴스 제목과 내용을 요약해줘.\n제목: {post.get('title', '')}\n내용: {post.get('message', '')}")
                        messages = [
                            {"role": "system", 
                             "content": 
                                """
                                안녕하세요, 뉴스 스크랩을 부탁드립니다. 형식은 아래와 같이 해주세요. 
                                내용 요약은 3줄 이내로 간단하게 작성하세요.
                                가독성이 높이기 위해 이모티콘를 포함해서 작성해 주세요.
                                """
                             },
                            {"role": "user", "content": prompt}
                        ]
                        response_text = ""
                        for chunk in model.stream(messages):
                            response_text += chunk.content
                        st.session_state["news_summaries"][idx] = response_text

                # 요약 결과 표 아래에 표시
                if st.session_state["news_summaries"]:
                    st.markdown("---")
                    st.subheader(":memo: 뉴스 요약 결과")
                    slack_url = os.getenv("SLACK_WEBHOOK_URL")
                    for idx, summary in st.session_state["news_summaries"].items():
                        post = board_list[idx]
                        st.markdown(f"**{post.get('title', '')}**")
                        st.write(summary)
                        # 슬랙 전송 버튼
                        if st.button(f"슬랙으로 전송하기", key=f"slack_btn_{idx}"):
                            if slack_url:
                                # HTML 태그 제거 후 텍스트만 슬랙으로 전송
                                msg = f"컴플라이언스 뉴스 요약\n제목: {post.get('title', '')}\n요약: {html_to_slack_text(summary)}"
                                try:
                                    resp = requests.post(slack_url, json={"text": msg})
                                    if resp.status_code == 200:
                                        st.success("슬랙으로 전송되었습니다.")
                                    else:
                                        st.error(f"슬랙 전송 실패: {resp.status_code}")
                                except Exception as e:
                                    st.error(f"슬랙 전송 오류: {e}")
                            else:
                                st.error("슬랙 Webhook URL이 설정되어 있지 않습니다.")
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
                    # 날짜 포맷 변경
                    from datetime import datetime
                    def format_date(date_str):
                        try:
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            return dt.strftime('%Y-%m-%d %H:%M')
                        except Exception:
                            return date_str
                    st.write(f"**날짜:** {format_date(post.get('createdate', ''))}")
                    st.markdown(f"---")
                    
                    raw_html = post.get("message", "")
                    soup = BeautifulSoup(raw_html, "html.parser")
                    st.write(soup.get_text(separator="\n"))
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