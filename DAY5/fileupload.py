import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import streamlit as st

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

st.title("Azure Blobk Stroage에 파일 업로드")
uploaded_file = st.file_uploader("업로드할 파일을 선택하세요", 
                                type=["png","jpg","jpeg","webp"])

if uploaded_file is not None:

    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        #blob_container = container_client.get_blob_client("image.png")
        blob_container = container_client.get_blob_client(uploaded_file.name)

        # with open("C:\\Users\\User\\Documents\\카카오톡 받은 파일\\KakaoTalk_20250919_143910645.jpg","rb") as data:
        #     blob_container.upload_blob(data, overwrite=True)
        blob_container.upload_blob(uploaded_file, overwrite=True)


        print("파일 업로드 성공!!!")
    except Exception as e:
        print(f"파일 업로드 실패: {e}")
