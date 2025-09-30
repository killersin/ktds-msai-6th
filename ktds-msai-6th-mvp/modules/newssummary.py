"""
컴플라이아언스 뉴스 요약 모듈
1. 게시글 목록/조회
2. 뉴스요약 -> 슬랙 전송
"""
import os
import requests
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup


def html_to_slack_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all('a'):
        url = a.get('href', '')
        text = a.get_text()
        slack_link = f'<{url}|{text}>' if url else text
        a.replace_with(slack_link)
    return soup.get_text(separator="\n")


def format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return date_str


def load_board_list(json_path: str) -> list:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def show_board(json_path: str = os.path.join('data', 'board_data.json')):
    # 세션 초기화
    if 'show_board' not in st.session_state:
        st.session_state['show_board'] = True

    # 안전: 이전에 남았을 수 있는 잔상 관련 세션 키들을 제거합니다.
    for k in ('detail_html', 'residual_message', 'temp_post_body'):
        if k in st.session_state:
            del st.session_state[k]

    # 요약 저장소
    if 'news_summaries' not in st.session_state:
        st.session_state['news_summaries'] = {}

    try:
        board_list = load_board_list(json_path)
    except Exception as e:
        st.error(f"게시글을 불러올 수 없습니다: {e}")
        return

    if not isinstance(board_list, list) or len(board_list) == 0:
        st.warning("게시글 데이터가 없습니다.")
        return

    # 사용자가 목록/상세 전환 시 잔상이 남지 않도록 빈 자리표시자를 사용합니다.
    root_ph = st.empty()
    try:
        # 초기 렌더 전에 혹시 남아있는 것을 비웁니다.
        root_ph.empty()
    except Exception:
        pass

    selected_post_idx = st.session_state.get('selected_post_idx', None)

    if selected_post_idx is None:
        with root_ph.container():
            # header
            header = st.columns([2, 10, 4, 4, 4, 4])
            header[0].markdown("**번호**")
            header[1].markdown("**제목**")
            header[2].markdown("**작성자**")
            header[3].markdown("**부서**")
            header[4].markdown("**날짜**")
            header[5].markdown("**뉴스요약**")

            for idx, post in enumerate(board_list):
                cols = st.columns([2, 10, 4, 4, 4, 4])
                cols[0].write(post.get('postid', ''))
                if cols[1].button(post.get('title', ''), key=f'title_btn_{idx}'):
                    # 상세로 진입할 때 이전 요약/상태를 초기화하고 자리표시자를 비웁니다.
                    st.session_state['news_summaries'] = {}
                    st.session_state['selected_post_idx'] = idx
                    try:
                        root_ph.empty()
                    except Exception:
                        pass
                    st.rerun()
                cols[2].write(post.get('username', ''))
                cols[3].write(post.get('detptname', ''))
                cols[4].write(format_date(post.get('createdate', '')))

                # 요약 버튼
                if cols[5].button('요약', key=f'summary_btn_{idx}'):
                    # reset previous summaries
                    st.session_state['news_summaries'] = {}
                    # lazy import model
                    from langchain_openai import AzureChatOpenAI
                    model = AzureChatOpenAI(
                        azure_endpoint=os.getenv('AZURE_ENDPOINT'),
                        api_key=os.getenv('OPENAI_API_KEY'),
                        api_version=os.getenv('AZURE_OPENAI_VERSION'),
                        azure_deployment='gpt-4.1-mini'
                    )
                    prompt = (f"다음 뉴스 제목과 내용을 요약해줘.\n제목: {post.get('title', '')}\n내용: {post.get('message', '')}")
                    messages = [
                        {"role": "system", "content": "안녕하세요, 뉴스 스크랩을 부탁드립니다. 형식은 아래와 같이 해주세요. 내용 요약은 3줄 이내로 간단하게 작성하세요. 가독성이 높이기 위해 이모티콘를 포함해서 작성해 주세요."},
                        {"role": "user", "content": prompt}
                    ]
                    response_text = ''
                    for chunk in model.stream(messages):
                        response_text += chunk.content
                    st.session_state['news_summaries'][idx] = response_text

            # show summaries under table
            if st.session_state.get('news_summaries'):
                st.markdown('---')
                st.subheader(':memo: 뉴스 요약 결과')
                slack_url = os.getenv('SLACK_WEBHOOK_URL')
                for idx, summary in st.session_state['news_summaries'].items():
                    post = board_list[idx]
                    st.markdown(f"**{post.get('title', '')}**")
                    st.write(summary)
                    if st.button(f"슬랙으로 전송하기", key=f"slack_btn_{idx}"):
                        if slack_url:
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
                            st.error('슬랙 Webhook URL이 설정되어 있지 않습니다.')

    else:
        with root_ph.container():
            if st.button('목록'):
                st.session_state['selected_post_idx'] = None
                st.session_state['news_summaries'] = {}
                if 'detail_html' in st.session_state:
                    del st.session_state['detail_html']
                try:
                    root_ph.empty()
                except Exception:
                    pass
                st.rerun()
            post = board_list[selected_post_idx]
            with st.container():
                st.subheader(post.get('title', ''))
                st.write(f"**번호:** {post.get('postid', '')}")
                st.write(f"**작성자:** {post.get('username', '')}")
                st.write(f"**부서:** {post.get('detptname', '')}")
                st.write(f"**날짜:** {format_date(post.get('createdate', ''))}")
                st.markdown('---')
                raw_html = post.get('message', '')
                soup = BeautifulSoup(raw_html, 'html.parser')
                st.write(soup.get_text(separator='\n'))
