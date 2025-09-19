import streamlit as st

# 세션 상태 초기화 (int로 이미 들어간 경우 방지)
if not isinstance(st.session_state.get("messages"), list):
    st.session_state.messages = []

# 이전 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력 처리
if prompt := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 출력 및 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 응답 생성 (Echo)
    response = f"Echo: {prompt}"
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)




# my_button = st.button("버튼")
# st.write(my_button)
# st.link_button("네이버","https://www.naver.com")
# st.write("안녕하세요")

# text_input = st.text_input("텍스트 입력")
# st.write(f"입력된 텍스트: {text_input}")

# uploaded_file = st.file_uploader("파일 업로드")
# if uploaded_file:
#     st.write(f"업로드된 파일명: {uploaded_file.name}")

# st_text="hello streamlit"
# st.text(st_text)
# st.markdown(
# """
# 테이블 정렬

# 헤더1|헤더2|헤더3
# :---|:---:|---:
# Left|Center|Right
# 1|2|3
# 4|5|6
# 7|8|9
# """)
# st.markdown("## 마크다운입니다.")
# st.markdown("**볼드**")

