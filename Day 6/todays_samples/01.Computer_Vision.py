import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from PIL import Image, ImageDraw, ImageFont #pip install pillow


load_dotenv()

COMPUTER_VISION_KEY = os.getenv("COMPUTER_VISION_KEY")
COMPUTER_VISION_ENDPOINT = os.getenv("COMPUTER_VISION_ENDPOINT")

credential = AzureKeyCredential(COMPUTER_VISION_KEY)

client = ImageAnalysisClient(endpoint=COMPUTER_VISION_ENDPOINT,
                             credential=credential)

def get_image_info():
    file_path = input("Enter image file path: ")

    with open(file_path, "rb") as image_file:
        image_data = image_file.read()

        result = client.analyze(
            image_data = image_data,
            visual_features =[
                VisualFeatures.TAGS,
                VisualFeatures.CAPTION,
                VisualFeatures.OBJECTS
            ],
            model_version = "latest"
        )

    #Caption을 출력하는 부분
    if result.caption is not None:
        print(f"Catpion: {result.caption.text} with confidence {result.caption.confidence:.2f}")

    #Tags를 출력하는 부분
    if result.tags is not None:
        print("Tags:")
        for tag in result.tags.list:
            print(f" - {tag.name} (confidence: {tag.confidence:.2f})")

    #Image에 Draw를 그리는 부분
    image = Image.open(file_path)
    draw = ImageDraw.Draw(image)
    
    #Objects를 출력하는 부분
    if result.objects is not None:
        print("Objects:")
        for obj in result.objects.list:
            print(f" - {obj.tags[0].name} (confidence: {obj.tags[0].confidence:.2f}) at location {obj.bounding_box}") #- Pomeranian (confidence: 0.81) at location {'x': 360, 'y': 190, 'w': 2612, 'h': 2249}
            
            x, y, w, h = obj.bounding_box["x"], obj.bounding_box["y"], obj.bounding_box["w"], obj.bounding_box["h"]
            #print(x, y, w, h)
            draw.rectangle(((x,y), (x+w,y+h)), outline="red", width=4)
            draw.text((x,y), obj.tags[0].name, fill="red")

    image.show()
    image.save("output.png")

if __name__ == "__main__":
    get_image_info()