import os
import streamlit as st

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

st.title("🤖 GPT-4o와 대화해보세요!")
st.caption("Azure OpenAI의 최신 GPT-4o-mini 모델을 사용한 스트리밍 챗봇입니다.")

model = AzureChatOpenAI(azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                        api_key=os.getenv("OPENAI_API_KEY"),
                        api_version = os.getenv("OPENAI_API_VERSION"),
                        azure_deployment="gpt-4o-mini")

if "messages" not in st.session_state:
    st.session_state["messages"]=[
        {"role":"system","content":"You are a helpful assistant."}
    ]
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("User : "):
    st.session_state["messages"].append({"role":"user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response_text = ""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        
        #response_text = model.invoke(st.session_state["messages"].content)
        #placeholder.markdown(response_text)
       
        for chunk in model.stream(st.session_state["messages"]):
            response_text += chunk.content
            placeholder.markdown(response_text)

    st.session_state["messages"].append({"role":"assistant", "content": response_text})