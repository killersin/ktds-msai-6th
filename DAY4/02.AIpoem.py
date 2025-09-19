import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
openai.azure_endpoint = os.getenv("AZURE_ENDPOINT")
openai.api_type = os.getenv("OPENAI_API_TYPE")
openai.api_version = os.getenv("OPENAI_API_VERSION")


subject = input("주제를 입력하세요: ")
content = input("시를 작성할 내용을 입력하세요.")

response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role":"system", "content":"You are a helpful assistant"},
        {"role":"user", "content":f"주제: {subject}\n내용:{content}\n 시를 작성해줘"}
    ]
)

print(response.choices[0].message.content)
