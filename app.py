from flask import Flask
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

app = Flask(__name__)

# 로그 핸들러 설정
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=6e15ba48-cdc5-4b3d-87c6-2bf76e29c11d;IngestionEndpoint=https://koreacentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://koreacentral.livediagnostics.monitor.azure.com/;ApplicationId=6b35c54a-d2e1-46fb-aadb-1c2fb772cda7'
))
logger.setLevel(logging.INFO)

@app.route('/')
def hello():
    logger.info("홈페이지 접속됨")
    return "Hello Azure with App Insights!"
if __name__ == '__main__':
    app.run(debug=True)