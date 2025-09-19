import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

load_dotenv()

embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version = "2024-02-01",
    azure_deployment="text-embedding-3-large"
)

documents = [
    "우리 할머니는 생일에만 끓여주던 비법 미역국이 있었다.",
    "대학교를 다닐 때, 유럽 여행을 간 적이 있다.",
    "우리 사무실 화이트 보드에는 예전에 그린 공룡 낙서가 있다."
]

vector_store = FAISS.from_texts(documents, embeddings)

query = "생일때 누가 미역국을 끓여줫지?"

results = vector_store.similarity_search(query, k=5)

print("검색결과")
for r in results:
    print("-", r.page_content)

llm = AzureChatOpenAI(azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                        api_key=os.getenv("OPENAI_API_KEY"),
                        api_version = os.getenv("OPENAI_API_VERSION"),
                        azure_deployment="gpt-4o-mini")

retrieval = vector_store.as_retriever(search_kwargs={"k":3})

prompt = ChatPromptTemplate.from_template(
"""
Context 안에 있는 정보를 바탕으로 질문에 답해줘.
<context>
{context}
</context>
질문 : {input}
"""
)

documnet_chain = create_stuff_documents_chain(llm, prompt)

retrieval_chain = create_retrieval_chain(retrieval, documnet_chain)

result = retrieval_chain.invoke({"input":query})

print("질문: ", query)
print("답변: ", result["answer"])

