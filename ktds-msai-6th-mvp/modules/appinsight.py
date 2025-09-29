"""
Application Insights 초기화 유틸리티

사용법:
from modules import appinsigjt
logger = appinsigjt.init_app_insights("my-app")
# 또는
from modules.appinsigjt import get_logger, register_excepthook
logger = get_logger()
register_excepthook(logger)

환경변수:
- APPLICATIONINSIGHTS_CONNECTION_STRING

이 모듈은 opencensus-ext-azure의 AzureLogHandler를 사용합니다.
"""

import os
import logging
import sys
from typing import Optional

_default_logger: Optional[logging.Logger] = None


def init_app_insights(name: str = __name__) -> logging.Logger:
    """Application Insights 핸들러를 붙인 logger를 반환합니다.

    name: 로거 이름
    반환값: 초기화된 logging.Logger
    """
    global _default_logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if _default_logger is not None and _default_logger is logger:
        return logger
    # 항상 콘솔(표준출력) 핸들러를 붙여 초기화 상태를 Kudu / App Service 로그에서 확인할 수 있도록 합니다.
    _attach_console_handler(logger)

    conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if conn_str:
        try:
            from opencensus.ext.azure.log_exporter import AzureLogHandler

            handler = AzureLogHandler(connection_string=conn_str)
            # 중복 추가 방지
            if not any(isinstance(h, type(handler)) for h in logger.handlers):
                logger.addHandler(handler)

            # 루트 로거에도 핸들러 추가 (다른 패키지 로그 캡처)
            root_logger = logging.getLogger()
            if not any(isinstance(h, type(handler)) for h in root_logger.handlers):
                root_logger.addHandler(handler)

            logger.info("Application Insights handler attached")
            # 콘솔에도 성공 메시지 표시
            logger.info("App Insights initialization successful (console+AI)")
        except Exception as e:
            # 패키지 미설치 또는 초기화 실패 시 콘솔에도 표시
            logger.warning(f"Failed to initialize Application Insights handler: {e}")
    else:
        logger.info("APPLICATIONINSIGHTS_CONNECTION_STRING not set; skipping App Insights initialization")

    _default_logger = logger
    return logger


def get_logger() -> logging.Logger:
    """모듈 전역 로거를 반환합니다. 초기화되지 않았으면 기본 이름으로 초기화합니다."""
    global _default_logger
    if _default_logger is None:
        _default_logger = init_app_insights()
    return _default_logger


def _attach_console_handler(logger: logging.Logger):
    """표준출력(console)으로 로그를 남기기 위한 StreamHandler를 추가합니다.

    App Service의 Kudu 또는 컨테이너 로그에서 바로 초기화 상태를 확인할 수 있도록 함.
    중복 핸들러 추가는 방지합니다.
    """
    try:
        # 이미 스트림 핸들러가 붙어있지 않으면 추가
        has_stream = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
        if not has_stream:
            sh = logging.StreamHandler(stream=sys.stdout)
            sh.setLevel(logging.INFO)
            fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
            sh.setFormatter(fmt)
            logger.addHandler(sh)
            # 루트 로거에도 동일 핸들러가 없다면 추가해둠
            root_logger = logging.getLogger()
            if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
                root_logger.addHandler(sh)
    except Exception:
        # 콘솔 핸들러 추가 실패시 무시(환경에 따라 제한적일 수 있음)
        pass


def _handle_exception(exc_type, exc_value, exc_traceback):
    # KeyboardInterrupt는 기본 훅으로 위임
    if exc_type is KeyboardInterrupt:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger = get_logger()
    logger.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


def register_excepthook(logger: Optional[logging.Logger] = None):
    """전역 예외 훅을 등록합니다. (미처리 예외를 Application Insights로 전송)

    logger: 사용할 로거(지정되지 않으면 모듈 로거 사용)
    """
    if logger is None:
        logger = get_logger()
    # 등록
    sys.excepthook = _handle_exception
    logger.info("Global excepthook registered")


def send_test_message(message: str = "App Insights test message") -> None:
    """테스트 정보를 로그로 보냅니다. 배포된 환경에서 로그가 Application Insights로 전송되는지 확인할 때 사용.

    예: modules.appinsigjt.send_test_message("hello from deployment")
    """
    logger = get_logger()
    logger.info(message)


def send_test_exception() -> None:
    """의도적으로 예외를 발생시켜 예외 로깅이 Application Insights에 전송되는지 확인합니다."""
    logger = get_logger()
    try:
        raise RuntimeError("App Insights test exception")
    except Exception:
        logger.exception("Test exception emitted to Application Insights")


# 모듈 import 시 자동 초기화(옵션)
get_logger()