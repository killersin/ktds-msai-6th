"""
Azure AI Search 모듈
RAG 파이프라인을 위한 벡터 검색 및 문서 인덱싱 담당

이 모듈은:
- Azure Search 인덱스(예: compliance-9fields) 생성
- 로컬 JSON 파일(`/data/9_field.json` 또는 대체 경로)의 항목을 인덱스에 업로드

환경 변수:
- AZURE_SEARCH_ENDPOINT
- AZURE_SEARCH_KEY
"""

import os
import json
import logging
from typing import Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
	SearchIndex,
	SearchField,
	SearchFieldDataType,
	SimpleField,
	SearchableField,
	VectorSearch,
	VectorSearchProfile,
	VectorSearchAlgorithmKind,
	VectorSearchAlgorithmMetric,
	HnswAlgorithmConfiguration,
)

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AzureSearchClient:
	"""Azure AI Search와 통신하는 간단한 클라이언트

	주목:
	- 이 모듈은 입력 JSON 구조가 두 가지 형태 중 하나일 것으로 가정합니다:
	  1) 리스트 형태: [{"category_no":1, "category":"부패방지", "content":"..."}, ...]
	  2) dict 형태: {"01_부패방지": ["내용1", "내용2", ...], ...}
	- 기본적으로 벡터 임베딩을 자동으로 생성하지 않습니다(필요 시 추후 확장 가능).
	"""

	def __init__(self):
		self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT") # Azure Search 엔드포인트
		# 키 환경변수명 호환성: AZURE_SEARCH_KEY 또는 AZURE_SEARCH_API_KEY
		self.key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
		# 인덱스 이름 환경변수도 여러명 지원
		self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") or os.getenv("AZURE_SEARCH_INDEX")
		# .env에 따옴표가 들어간 경우 제거
		if self.index_name:
			self.index_name = self.index_name.strip().strip('"').strip("'")

		if not self.endpoint or not self.key:
			raise ValueError("AZURE_SEARCH_ENDPOINT 또는 AZURE_SEARCH_API_KEY/AZURE_SEARCH_KEY 환경변수가 필요합니다.")

		self.credential = AzureKeyCredential(self.key)
		self.index_client = SearchIndexClient(endpoint=self.endpoint, credential=self.credential)
		logger.info("Azure SearchIndexClient 초기화 완료")

	def create_compliance_index(self) -> bool:
		"""컴플라이언스(9개 분야)용 인덱스 생성

		- content(검색가능), category/ category_no 필터 가능
		- content_vector 필드는 벡터 검색을 위해 준비되어 있음(임베딩이 있을 때 업로드 가능)
		"""
		try:
			vector_search = VectorSearch(
				profiles=[
					VectorSearchProfile(name="default-profile", algorithm_configuration_name="default-hnsw")
				],
				algorithms=[
					HnswAlgorithmConfiguration(
						name="default-hnsw",
						kind=VectorSearchAlgorithmKind.HNSW,
						parameters={
							"m": 4,
							"efConstruction": 400,
							"efSearch": 500,
							"metric": VectorSearchAlgorithmMetric.COSINE,
						},
					)
				],
			)

			fields = [
				SimpleField(name="id", type=SearchFieldDataType.String, key=True),
				SimpleField(name="category_no", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
				SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
				SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name=None),
				SimpleField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=False),
				SimpleField(name="item_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
				SearchField(
					name="content_vector",
					type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
					searchable=True,
					vector_search_dimensions=1536,
					vector_search_profile_name="default-profile",
				),
			]

			index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)

			result = self.index_client.create_or_update_index(index)
			logger.info(f"인덱스 생성/업데이트 완료: {result.name}")
			return True

		except Exception as e:
			logger.exception("인덱스 생성 실패")
			return False

	def get_search_client(self) -> SearchClient:
		return SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)

	def ensure_index_exists(self) -> bool:
		"""인덱스가 존재하는지 확인하고 없으면 생성한다."""
		try:
			# 존재 여부 확인
			self.index_client.get_index(self.index_name)
			logger.info(f"인덱스가 이미 존재합니다: {self.index_name}")
			return True
		except Exception:
			logger.info(f"인덱스를 찾을 수 없습니다. 생성 시도: {self.index_name}")
			return self.create_compliance_index()

	def _load_json_candidates(self, paths: List[str]) -> Optional[object]:
		"""여러 후보 경로에서 첫 번째로 존재하는 JSON을 로드하여 반환"""
		for p in paths:
			if os.path.exists(p):
				try:
					with open(p, "r", encoding="utf-8") as f:
						return json.load(f)
				except Exception:
					logger.exception(f"JSON 로드 실패: {p}")
		return None

	def index_from_file(self, file_path: str = None, batch_size: int = 200) -> Dict:
		"""로컬 JSON 파일을 읽어 인덱스에 업로드

		file_path 우선순위:
		1) 전달된 file_path
		2) ./data/9_field.json
		3) ./data/9_domains.json
		4) ./data/test.json
		"""
		candidates = []
		if file_path:
			candidates.append(file_path)
		candidates.extend([
			os.path.join("data", "9_field.json"),
			os.path.join("data", "9_domains.json"),
			os.path.join("data", "test.json"),
		])

		data = self._load_json_candidates(candidates)
		if data is None:
			raise FileNotFoundError("인덱싱할 JSON 파일을 찾을 수 없습니다. 후보: " + ",".join(candidates))

		# 문서 목록으로 변환
		docs = []
		if isinstance(data, dict):
			# 형태: {"01_부패방지": [...], ...}
			for cat_key, items in data.items():
				for idx, item in enumerate(items):
					docs.append({
						"id": f"{cat_key}-{idx}",
						"category": cat_key,
						"category_no": None,
						"content": item,
						"source": os.path.basename(candidates[0]),
						"item_index": idx,
					})
		elif isinstance(data, list):
			# 리스트의 각 항목이 dict(이미 구조화)인 경우
			for idx, item in enumerate(data):
				if isinstance(item, dict):
					cid = item.get("id") or f"{item.get('category_no','')}-{idx}"
					docs.append({
						"id": str(cid),
						"category": item.get("category") or item.get("category", ""),
						"category_no": item.get("category_no"),
						"content": item.get("content") or item.get("text") or json.dumps(item, ensure_ascii=False),
						"source": os.path.basename(candidates[0]),
						"item_index": idx,
					})
				else:
					# 단순 문자열 리스트
					docs.append({
						"id": f"item-{idx}",
						"category": None,
						"category_no": None,
						"content": str(item),
						"source": os.path.basename(candidates[0]),
						"item_index": idx,
					})
		else:
			raise ValueError("지원되지 않는 JSON 구조입니다.")

		# 배치 업로드
		# 인덱스가 존재하는지 확인(없으면 생성)
		self.ensure_index_exists()
		client = self.get_search_client()
		total = len(docs)
		success = 0
		failed = 0
		for i in range(0, total, batch_size):
			batch = docs[i : i + batch_size]
			try:
				result = client.upload_documents(documents=batch)
				for r in result:
					if getattr(r, "succeeded", False):
						success += 1
					else:
						failed += 1
						logger.error(f"업로드 실패: {getattr(r, 'error_message', r)}")
			except Exception:
				logger.exception("배치 업로드 중 오류")
				failed += len(batch)

		return {"total": total, "success": success, "failed": failed}


def main_create_and_index(file_path: str = None):
	client = AzureSearchClient()
	print("🔄 인덱스 생성중...")
	if client.create_compliance_index():
		print("✅ 인덱스 생성/업데이트 완료")
	else:
		print("❌ 인덱스 생성 실패")

	print("🔄 파일을 인덱싱 중입니다...")
	try:
		res = client.index_from_file(file_path=file_path)
		print(f"✅ 인덱싱 완료: 총={res['total']}, 성공={res['success']}, 실패={res['failed']}")
	except Exception as e:
		print(f"❌ 인덱싱 실패: {e}")


if __name__ == "__main__":
	# 스크립트로 실행할 때 기본 경로 사용
	main_create_and_index()


