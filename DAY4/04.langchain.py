import openai
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

# openai.api_key = os.getenv("OPENAI_API_KEY")
# openai.azure_endpoint = os.getenv("AZURE_ENDPOINT")
# openai.api_type = os.getenv("OPENAI_API_TYPE")
# openai.api_version = os.getenv("OPENAI_API_VERSION")

messages = [{"role":"system", "content":"You are a helpful assistant."}]
model = AzureChatOpenAI(azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                        api_key=os.getenv("OPENAI_API_KEY"),
                        api_version = os.getenv("OPENAI_API_VERSION"),
                        azure_deployment="gpt-4o-mini")

while True:

    user_input = input("User: ")
    messages.append({"role":"user", "content": user_input})

    response = model.invoke(messages)

    messages.append({"role":"assistant", "content": response.content})

    print(f"Assistant : {response.content}")
