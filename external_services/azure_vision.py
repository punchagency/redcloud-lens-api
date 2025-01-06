# pip install azure-cognitiveservices-vision-customvision
# pip install azure-storage-blob
# pip install Pillow
# pip install loguru

import base64
import io
import sys
from typing import Optional, Dict, Any
from azure.cognitiveservices.vision.customvision.prediction import (
    CustomVisionPredictionClient,
)
from msrest.authentication import ApiKeyCredentials
from PIL import Image
from loguru import logger
import os

# Set up logging with loguru
logger.remove()  # Remove default logger

# Console handler with colorful output
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>",
    colorize=True,
)

# File handler for logging to a text file
logger.add(
    "azure_vision_service.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="1 week",
)

# ENVIRONMENT VARIABLES
VISION_PREDICTION_KEY = "6V48E35SMe82iANGYug53V5pRsp0XHZY1iyGkkgRL5MfLAAWTOavJQQJ99BAACLArgHXJ3w3AAAIACOGVsrv"  # "FcUbyj3heEP6O75TkMplbb0iplwD9FNS722RAdQTo82AwmmSiSI1JQQJ99BAACLArgHXJ3w3AAAJACOGvXSm"
VISION_PREDICTION_ENDPOINT = "https://redcloudlens-prediction.cognitiveservices.azure.com/"  # "https://redcloudlens-prediction.cognitiveservices.azure.com/customvision/v3.0/Prediction/e3d70115-4fd8-435d-bc8f-99b5927ff50a/classify/iterations/redcloudlens/image"
VISION_PROJECT_ID = "e3d70115-4fd8-435d-bc8f-99b5927ff50a"
VISION_ITERATION_NAME = "redcloudlens"


class AzureVisionService:
    """
    A service to interact with Azure Custom Vision for image classification tasks.
    This service maintains the same interface as the VertexAIService for easy swapping.
    """

    def __init__(
        self,
        prediction_key: str,
        endpoint: str,
        project_id: str,
        publish_iteration_name: str = "Iteration 1",
    ):
        """
        Initialize the Azure Custom Vision service.

        Args:
            prediction_key (str): The prediction key from Azure Custom Visionz
            endpoint (str): The endpoint URL for your Custom Vision service
            project_id (str): The project ID from Azure Custom Vision
            publish_iteration_name (str): The iteration name to use for predictions
        """
        self.project_id = project_id
        self.publish_iteration_name = publish_iteration_name

        # Initialize the prediction client
        credentials = ApiKeyCredentials(in_headers={"Prediction-key": prediction_key})
        self.predictor = CustomVisionPredictionClient(endpoint, credentials)

    def encode_image_to_base64(self, image: Image.Image) -> str:
        """
        Convert a PIL image to a base64 encoded string.

        Args:
            image: A PIL Image object to be converted.
        Returns:
            str: A base64 encoded string representing the image.
        """
        try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="JPEG")
            img_byte_arr = img_byte_arr.getvalue()
            base64_str = base64.b64encode(img_byte_arr).decode("utf-8")
            return base64_str
        except Exception as e:
            logger.error(f"Failed to encode image to base64: {str(e)}")
            return None

    def classify_image(self, image: str) -> Optional[Dict[str, Any]]:
        """
        Classifies an image using Azure Custom Vision.

        Args:
            image: Either a base64 encoded string or a PIL Image object
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing prediction results or None if failed
        """
        try:
            # Handle both base64 string and PIL Image inputs
            # if isinstance(image, str):
            #     # If it's a base64 string, decode it to bytes
            #     image_data = base64.b64decode(image)
            #     image_stream = io.BytesIO(image_data)
            # elif isinstance(image, Image.Image):
            #     # If it's a PIL Image, convert to bytes
            #     image_stream = io.BytesIO()
            #     image.save(image_stream, format="JPEG")
            #     image_stream.seek(0)
            # else:
            #     logger.error("Invalid image format provided")
            #     return None

            # Make prediction using the image stream
            # results = self.predictor.classify_image_url_with_no_store(
            #     self.project_id, self.publish_iteration_name, image_stream
            # )

            with open(image, "rb") as image_contents:
                results = self.predictor.classify_image(
                    self.project_id, self.publish_iteration_name, image_contents.read()
                )

            # Process results
            if results.predictions:
                # Get the highest confidence prediction
                top_prediction = max(results.predictions, key=lambda x: x.probability)
                return {
                    "label": top_prediction.tag_name,
                    "confidence": float(top_prediction.probability),
                }

            logger.warning("No predictions returned from Azure Custom Vision")
            return None

        except Exception as e:
            logger.error(f"Error during image classification: {str(e)}")
            return None

    def add_to_retraining_queue(self, image_path: str, image_name: str):
        """
        Uploads failed images to Azure Blob Storage for retraining.

        Args:
            image_path (str): The local file path of the image
            image_name (str): The name of the image
        """
        try:
            from azure.storage.blob import BlobServiceClient

            logger.info(f"Adding {image_name} to retraining queue")

            # Initialize blob service client (requires connection string)
            connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if not connect_str:
                logger.error(
                    "Azure Storage connection string not found in environment variables"
                )
                return

            blob_service_client = BlobServiceClient.from_connection_string(connect_str)

            # Get container client (create if doesn't exist)
            container_name = "retraining-queue"
            container_client = blob_service_client.get_container_client(container_name)

            if not container_client.exists():
                container_client.create_container()

            # Upload blob
            blob_client = container_client.get_blob_client(f"retraining/{image_name}")
            with open(image_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            logger.info(f"Image {image_name} uploaded to retraining queue")

        except Exception as e:
            logger.error(f"Failed to upload {image_name} to retraining queue: {str(e)}")

    def process_and_classify_image(
        self, image: str, image_name: str, confidence_threshold: float = 0.60
    ) -> Optional[Dict[str, Any]]:
        """
        Processes an image: classifies it and handles failed predictions by adding them to the retraining queue.

        Args:
            image: The image to be classified (base64 string or PIL Image)
            image_name: The name of the image
            confidence_threshold: The minimum confidence score to consider the prediction valid
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing prediction results or None if failed
        """
        try:
            result = self.classify_image(image_name)

            if result:
                if result["confidence"] < confidence_threshold:
                    logger.warning(
                        f"Prediction confidence ({result['confidence']}) is below threshold for image {image_name}"
                    )
                    self.add_to_retraining_queue(image_name, image_name)
                else:
                    logger.info(
                        f"Image {image_name} classified as {result['label']} with confidence {result['confidence']}"
                    )
                return result
            else:
                logger.error(
                    f"Failed to classify image {image_name}. Adding to retraining queue."
                )
                self.add_to_retraining_queue(image_name, image_name)
                return None

        except Exception as e:
            logger.error(f"Error processing image {image_name}: {str(e)}")
            self.add_to_retraining_queue(image_name, image_name)
            return None


# Example usage
if __name__ == "__main__":
    # Initialize the service with your Azure Custom Vision credentials
    service = AzureVisionService(
        prediction_key=VISION_PREDICTION_KEY,
        endpoint=VISION_PREDICTION_ENDPOINT,
        project_id=VISION_PROJECT_ID,
        publish_iteration_name=VISION_ITERATION_NAME,
    )

    # Example image to process
    image_path = "./chivital-mama-cass.jpg"
    image = Image.open(image_path)

    # Process and classify the example image
    result = service.process_and_classify_image(image, image_path)
    if result:
        print(f"Classification result: {result}")
        # 2025-01-06 07:35:07 | Image ./chivital-mama-cass.jpg classified as Chivita_b52930348a1b4 with confidence 0.63868046
        # Classification result: {'label': 'Chivita_b52930348a1b4', 'confidence': 0.63868046}
