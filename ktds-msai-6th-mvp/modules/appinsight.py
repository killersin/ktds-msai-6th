"""
Application Insights 연동 모듈

이 모듈은 애플리케이션 시작 시 Application Insights(Azure Monitor)로
로그와 트레이스를 전송하도록 설정하는 헬퍼를 제공합니다.

사용법:
	from modules.appinsight import init_appinsights
	logger = init_appinsights()

환경 변수:
	APPLICATIONINSIGHTS_CONNECTION_STRING - Application Insights 연결 문자열

주의: 환경 변수가 설정되어 있지 않으면 아무 작업도 하지 않고 None을 반환합니다.
"""

import os
import logging
from contextlib import contextmanager

try:
	# opencensus 기반 Azure exporter 사용
	from opencensus.ext.azure.log_exporter import AzureLogHandler
	from opencensus.ext.azure.trace_exporter import AzureExporter
	from opencensus.trace.tracer import Tracer
	from opencensus.trace.samplers import ProbabilitySampler
	from opencensus.trace import config_integration
except Exception:
	# 패키지가 없으면 import 에러를 발생시키지 않도록 처리
	AzureLogHandler = None
	AzureExporter = None
	Tracer = None
	ProbabilitySampler = None
	config_integration = None


def init_appinsights(service_name: str | None = None):
	"""
	Application Insights 초기화 함수.

	- APPLICATIONINSIGHTS_CONNECTION_STRING 환경변수를 읽어 설정합니다.
	- logging과 requests에 대한 opencensus 통합을 등록합니다.
	- AzureLogHandler를 전역 로거에 추가하고, Tracer를 생성합니다.

	반환값: 로그/트레이스에 사용할 간단한 래퍼 객체 또는 환경변수가 없거나 실패 시 None
	"""
	conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
	if not conn_str:
		# 환경변수가 설정되어 있지 않으면 아무 작업도 하지 않음
		return None

	if AzureLogHandler is None:
		# 필요한 패키지가 설치되어 있지 않음
		logging.getLogger().warning("opencensus 패키지가 설치되어 있지 않아 Application Insights 초기화를 건너뜁니다.")
		return None

	try:
		# opencensus의 통합을 등록하여 requests, logging 등 자동 계측
		try:
			config_integration.trace_integrations(['logging', 'requests'])
		except Exception:
			# 통합 등록은 실패해도 계속 진행
			pass

		# 전역 로거에 AzureLogHandler 추가
		handler = AzureLogHandler(connection_string=conn_str)
		handler.setLevel(logging.INFO)

		root_logger = logging.getLogger()
		root_logger.setLevel(logging.INFO)
		root_logger.addHandler(handler)

		# 애플리케이션 이름(역할) 자동 설정: service_name이 있으면 ai.cloud.role 태그에 추가
		# Azure Portal에서 역할(role)별 필터링/대시보드 구성이 쉬워집니다.
		def _make_role_processor(role_name: str | None, role_instance: str | None = None):
			def _processor(envelope):
				try:
					# envelope.tags은 dict 형식이며 ai.cloud.role, ai.cloud.roleInstance 키를 사용합니다.
					if role_name:
						envelope.tags['ai.cloud.role'] = role_name
					if role_instance:
						envelope.tags['ai.cloud.roleInstance'] = role_instance
				except Exception:
					pass
			return _processor

		# 역할 이름을 환경변수나 전달값에서 유추
		if service_name:
			handler.add_telemetry_processor(_make_role_processor(service_name, os.getenv('WEBSITE_INSTANCE_ID')))
		else:
			# 웹앱으로 배포시 WEBSITE_SITE_NAME 환경변수를 사용하면 역할명으로 표시됩니다.
			handler.add_telemetry_processor(_make_role_processor(os.getenv('WEBSITE_SITE_NAME'), os.getenv('WEBSITE_INSTANCE_ID')))

		# 트레이스 Exporter 및 Tracer 생성 (샘플링은 전체 전송으로 설정)
		exporter = AzureExporter(connection_string=conn_str)
		tracer = Tracer(exporter=exporter, sampler=ProbabilitySampler(1.0))

		# 간단한 래퍼 객체 반환 (logger와 tracer 접근용)
		class _AIClient:
			def __init__(self, logger, tracer):
				self.logger = logger
				self.tracer = tracer

			def info(self, msg, *args, **kwargs):
				self.logger.info(msg, *args, **kwargs)

			def warning(self, msg, *args, **kwargs):
				self.logger.warning(msg, *args, **kwargs)

			def error(self, msg, *args, **kwargs):
				self.logger.error(msg, *args, **kwargs)

			def exception(self, msg, *args, **kwargs):
				self.logger.exception(msg, *args, **kwargs)

			def track_event(self, name: str, properties: dict | None = None):
				"""간단한 커스텀 이벤트를 traces로 전송합니다 (포털에서 customEvents 또는 traces로 확인 가능)."""
				try:
					if properties:
						self.logger.info(f"[EVENT] {name} | {properties}")
					else:
						self.logger.info(f"[EVENT] {name}")
				except Exception:
					pass

			@contextmanager
			def span(self, name: str):
				"""트레이스 span을 간단히 사용할 수 있는 컨텍스트 매니저 반환"""
				with self.tracer.span(name=name):
					yield

		return _AIClient(root_logger, tracer)
	except Exception:
		# 초기화 실패 시 아무 영향 없이 None 반환
		return None
