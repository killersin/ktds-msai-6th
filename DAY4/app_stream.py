# file: app_stream.py
import os, sys
from dotenv import load_dotenv  # ✅ 이거 추가

# ✅ .env 파일 로드 (현재 디렉토리 기준)
load_dotenv()

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
api_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt5-chat")

llm = AzureChatOpenAI(
		azure_endpoint=endpoint,
		api_key=api_key,
		api_version=api_version,
		azure_deployment=DEPLOYMENT_NAME,
		temperature=0.5,
)

prompt = ChatPromptTemplate.from_messages([
	("system", "너는 실전형 요약 비서야. 답변은 번호 매긴 3~5단계로, 각 단계는 한 문장. 실행 가능한 동사로 시작하고 과장된 표현은 피해."),
	("user", "{question}"),
])
chain = prompt | llm | StrOutputParser()

if __name__ == "__main__":
	for chunk in chain.stream({
		"question": "퇴근 후 30분 안에 만들 수 있는 건강한 저녁 메뉴 3가지를 추천해줘. 대략적인 재료비도 알려줘."
	}):
		sys.stdout.write(chunk)
		sys.stdout.flush()
	print()