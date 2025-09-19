import openai
import os
import streamlit as st

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

messages = [{"role":"system", "content":"You are a helpful assistant."}]
model = AzureChatOpenAI(azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                        api_key=os.getenv("OPENAI_API_KEY"),
                        api_version = os.getenv("OPENAI_API_VERSION"),
                        azure_deployment="gpt-4o-mini")

user_input = st.text_input("User : ")
button_click = st.button("AI 응답 생성")

if button_click:
    messages.append({"role":"user", "content": user_input})
    response = model.invoke(messages)
    messages.append({"role":"assistant", "content": response.content})

    st.write(f"Assistant : {response.content}")
    st.success("AI 응답이 생성되었씁니다!")
