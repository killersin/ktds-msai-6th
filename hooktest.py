import requests
import json

# 슬랙 Webhook URL
slack_webhook_url = 'https://hooks.slack.com/services/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'

# 보낼 메시지 내용
message = {
    "text": "📢 컴플라이언스 뉴스 요약: 오늘의 주요 법령 변경 사항이 업데이트되었습니다."
}

# 슬랙으로 POST 요청 보내기
response = requests.post(
    slack_webhook_url,
    data=json.dumps(message),
    headers={'Content-Type': 'application/json'}
)

# 응답 확인
if response.status_code == 200:
    print("슬랙 메시지 전송 성공!")
else:
    print(f"전송 실패: {response.status_code}, {response.text}")