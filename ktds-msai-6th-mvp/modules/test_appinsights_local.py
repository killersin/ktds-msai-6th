"""
로컬에서 Application Insights 연결을 간단히 테스트하는 스크립트

사용법 (PowerShell 예시):
  $env:APPLICATIONINSIGHTS_CONNECTION_STRING = "<your-connection-string>"
  python .\modules\test_appinsights_local.py

환경변수가 설정되어 있지 않으면 아무 동작도 하지 않습니다.
"""
import os
import time
import logging
import sys
from pathlib import Path

# 스크립트를 modules 폴더에서 직접 실행할 때 상위 프로젝트 루트를 import 경로에 추가합니다.
# 이렇게 하면 'No module named "modules"' 오류를 방지합니다.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from modules.appinsight import init_appinsights


# 프로젝트 루트의 .env 파일을 자동으로 로드합니다. (있으면 환경변수를 채워줍니다)
load_dotenv(ROOT_DIR / '.env')


# opencensus 패키지 설치 여부 간단 체크
try:
    import opencensus.ext.azure  # noqa: F401
except Exception:
    print("경고: opencensus 패키지가 설치되어 있지 않거나 import에 실패했습니다. 'pip install opencensus-ext-azure opencensus-ext-requests opencensus-ext-logging' 를 실행하세요.")


def main():
    # init_appinsights는 환경변수 APPLICATIONINSIGHTS_CONNECTION_STRING을 사용합니다.
    client = init_appinsights()
    if not client:
        print("Application Insights가 초기화되지 않았습니다. 환경변수 APPLICATIONINSIGHTS_CONNECTION_STRING을 설정했는지 확인하세요.")
        return

    # 로그 전송 테스트
    print("Application Insights 초기화 완료. 테스트 로그를 전송합니다...")
    client.info("[테스트] Application Insights에 info 로그 전송 테스트 신영철")
    time.sleep(0.5)

    # 예외 전송 테스트 (exception 사용)
    try:
        raise ValueError("테스트 예외: 로컬 전송 확인용")
    except Exception as e:
        client.exception(f"[테스트] 예외 전송: {e}")

    # 트레이스(스팬) 테스트
    with client.span("local-test-span"):
        client.info("스팬 내부에서 로그 기록")
        time.sleep(0.2)

    print("테스트 전송 완료. Azure Portal의 Live Metrics / Logs에서 확인하세요.")


if __name__ == '__main__':
    main()
