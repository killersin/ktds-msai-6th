import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.tools import Tool
from langchain.agents import initialize_agent

load_dotenv()

llm = AzureChatOpenAI(azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                        api_key=os.getenv("OPENAI_API_KEY"),
                        api_version = os.getenv("OPENAI_API_VERSION"),
                        azure_deployment="gpt-4o-mini")

def get_weather(city):
    """주어진 도시에 대해 맞는 날씨 정보를 가져옵니다."""
    return f"{city}의 날씨는 맑고 기온은 23도 입니다."

def recommed_outfit(temp: int):
    """주어진 기온에 맞는 적절한 옷차림을 추천합니다."""
    if isinstance(temp, str):
        temp = int(temp)

    if temp >25:
        return "반팔, 반바지"
    elif temp > 20:
        return "얇은 셔츠, 면바지"
    else:
        return "긴팔, 긴바지"

weather_tool = Tool(
    name="get_weather",
    func=get_weather,
    description="주어진 도시에 대해 맞는 날씨 정보를 가져옵니다."
)

outfit_tool = Tool(
    name="recomment_outfit",
    func=recommed_outfit,
    description="주어진 기온에 맞는 적절한 옷차림을 추천해줘."
)


tools = [weather_tool, outfit_tool]
agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

response = agent.run("서울의 날씨를 알려줘. 그리고 날씨에 맞는 옷차림을 추천해줘")
print(response)
