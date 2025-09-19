import os, sys
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

llm = AzureChatOpenAI(azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                        api_key=os.getenv("OPENAI_API_KEY"),
                        api_version = os.getenv("OPENAI_API_VERSION"),
                        azure_deployment="gpt-4o-mini")

prompt = ChatPromptTemplate.from_messages([
    ("system","You are a helpful assistant."),
    ("user","{question}")
])

post_format = ChatPromptTemplate.from_template(
"""
다음 답변을 발표 슬라이드용으로 만들어줘.
- 불릿은 5개이하
- 각 불릿은 12단어 이하 한국어 문장
- 지나친 전문용어는 줄이고, 명확한 표현 사용
원문

```
{raw}
```
"""
)

parser = StrOutputParser()
chain = prompt | llm | parser
polish_chain = ({"raw": chain}) | post_format | llm | parser

for chunk in polish_chain.stream({
    "question":"IT 개발자 커리어에 도움될 기술 5개 추천해줘."
}):
    sys.stdout.write(chunk)
    sys.stdout.flush()
