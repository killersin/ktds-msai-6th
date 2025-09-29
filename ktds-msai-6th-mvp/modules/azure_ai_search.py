"""
Azure AI Search 모듈
RAG 파이프라인을 위한 벡터 검색 및 문서 인덱싱 담당

이 모듈 기능:
- Azure Search 인덱스(예: compliance-9fields) 생성
- 로컬 JSON 파일(`/data/9_field.json` 또는 대체 경로)의 항목을 인덱스에 업로드

필요 환경변수:
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

	참고:
	- 입력 JSON 형식은 두 가지 중 하나를 지원합니다:
	  1) 리스트 형태: [{"category_no":1, "category":"부패방지", "content":"..."}, ...]
	  2) dict 형태: {"01_부패방지": ["내용1", "내용2", ...], ...}
	- 현재 이 모듈은 자동으로 임베딩을 생성하지 않습니다. 임베딩이 필요할 경우 환경변수를 통해 활성화됩니다.
	"""

	def __init__(self):
		self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")  # Azure Search 엔드포인트
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
				SimpleField(name="domain", type=SearchFieldDataType.String, filterable=True),
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
		"""인덱스 존재 여부 확인 후 없으면 생성한다."""
		try:
			# 인덱스 존재 여부 확인
			self.index_client.get_index(self.index_name)
			logger.info(f"인덱스가 이미 존재합니다: {self.index_name}")
			return True
		except Exception:
			logger.info(f"인덱스를 찾을 수 없습니다. 생성을 시도합니다: {self.index_name}")
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
		2) ./data/9_field.json
		"""
		candidates = []
		if file_path:
			candidates.append(file_path)
		candidates.extend([
			os.path.join("data", "9_field.json")
		])

		data = self._load_json_candidates(candidates)
		if data is None:
			raise FileNotFoundError("인덱싱할 JSON 파일을 찾을 수 없습니다. 후보: " + ",".join(candidates))

	# JSON을 문서 목록 형식으로 변환
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
						"domain": item.get("domain"),
						"content": item.get("content") or item.get("text") or json.dumps(item, ensure_ascii=False),
						"source": os.path.basename(candidates[0]),
						"item_index": idx,
					})
				else:
					# 단순 문자열 리스트 처리
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

	# 배치 업로드 전 추가 처리
	# --- 카테고리별 통합(doc per category) 문서 생성 ---
	# 같은 카테고리의 content들을 합쳐 별도의 요약/집계 문서를 생성하면
	# "컴플라이언스 9대분야 설명해줘" 같은 질문에 더 적합한 컨텍스트가 됩니다.
		agg_map = {}
		for d in docs:
			cat_key = d.get("category") or str(d.get("category_no")) or "unknown"
			agg_map.setdefault(cat_key, []).append(d.get("content", ""))

		for cat, pieces in agg_map.items():
			# 기존 문서에서 대표 category_no를 가져오려고 시도
			cat_no = None
			for d in docs:
				if d.get("category") == cat and d.get("category_no") is not None:
					cat_no = d.get("category_no")
					break

			agg_doc = {
				"id": f"cat-{cat_no or cat}",
				"category": cat,
				"category_no": cat_no,
				"domain": "컴플라이언스 9대분야",
				"content": "\n\n".join(pieces),
				"source": os.path.basename(candidates[0]),
				"item_index": -1,
			}
			docs.append(agg_doc)

	# 배치 업로드 준비

	# --- 임베딩 생성(선택) ---
	# 환경변수로 임베딩 모델/엔드포인트/키가 설정되어 있으면
	# 각 문서에 'content_vector' 필드를 추가합니다. 실패하면 벡터 없이 업로드합니다.
		embedding_model = os.getenv("AZURE_EMBEDDING_DEPLOYMENT") or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
		oa_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
		oa_endpoint = os.getenv("AZURE_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")

		if embedding_model and oa_key and oa_endpoint:
			try:
				emb_client = OpenAIClient(oa_endpoint, AzureKeyCredential(oa_key))
				# 작은 배치로 나눠 임베딩 생성
				chunk = 20
				for i in range(0, len(docs), chunk):
					inputs = [d.get("content", "") for d in docs[i : i + chunk]]
					try:
						resp = emb_client.embeddings.create(model=embedding_model, input=inputs)
						for j, item in enumerate(resp.data):
							vec = item.embedding
								# 해당 문서에 벡터 할당
							docs[i + j]["content_vector"] = vec
					except Exception:
						logger.exception("임베딩 생성 중 오류 발생(해당 배치는 건너뜁니다)")
						# 이 배치는 벡터 없이 계속 진행
						continue
			except Exception:
				logger.exception("임베딩 클라이언트 초기화 실패 - 벡터를 생성하지 않습니다.")
		else:
			logger.info("임베딩 환경변수 미설정 - content_vector를 생성하지 않습니다.")

	# 배치 업로드
	# 인덱스 존재 확인(없으면 생성)
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


