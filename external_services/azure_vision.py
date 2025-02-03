import base64
import io
import os
import sys
import uuid
from typing import Any, Dict, Optional

from azure.cognitiveservices.vision.customvision.prediction import (
    CustomVisionPredictionClient,
)
from loguru import logger
from msrest.authentication import ApiKeyCredentials
from PIL import Image

from routers.nlq.helpers import azure_vision_service
from settings import get_settings

settings = get_settings()

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
VISION_PREDICTION_KEY = settings.VISION_PREDICTION_KEY
VISION_PREDICTION_ENDPOINT = settings.VISION_PREDICTION_ENDPOINT
VISION_PROJECT_ID = settings.VISION_PROJECT_ID
VISION_ITERATION_NAME = settings.VISION_ITERATION_NAME


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
        temp_dir: str = "temp_images",
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

        self.temp_dir = temp_dir

        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)

        # Initialize the prediction client
        credentials = ApiKeyCredentials(in_headers={"Prediction-key": prediction_key})
        self.predictor = CustomVisionPredictionClient(endpoint, credentials)

    def base64_to_jpg(self, base64_string: str) -> str:
        """Convert base64 string to jpg file and return the file path."""
        try:
            # Remove header if present
            if "base64," in base64_string:
                base64_string = base64_string.split("base64,")[1]

            # Generate temporary file path
            temp_filename = f"{uuid.uuid4()}.jpg"
            temp_path = os.path.join(self.temp_dir, temp_filename)

            # Decode and save image
            image_data = base64.b64decode(base64_string)
            with open(temp_path, "wb") as f:
                f.write(image_data)

            logger.info(f"Converted base64 to jpg: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Failed to convert base64 to jpg: {str(e)}")

    def delete_jpg(self, file_path: str):
        """Delete the temporary jpg file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")

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

    def classify_image(self, base64_image: str) -> Optional[Dict[str, Any]]:
        """Classify a base64 encoded image."""
        temp_path = None

        try:
            # Convert base64 to jpg
            temp_path = self.base64_to_jpg(base64_image)

            # Run inference
            with open(temp_path, "rb") as image_file:
                results = self.predictor.classify_image(
                    self.project_id, self.publish_iteration_name, image_file.read()
                )

            # Process results
            if results.predictions:
                top_prediction = max(results.predictions, key=lambda x: x.probability)
                return {
                    "label": top_prediction.tag_name,
                    "confidence": float(top_prediction.probability),
                }

            logger.warning("No predictions returned")
            return None

        except Exception as e:
            logger.error(f"Error during classification: {str(e)}")
            return None

        finally:
            # Clean up temporary file
            if temp_path:
                self.delete_jpg(temp_path)

    def add_to_retraining_queue(self, base64_image: str, image_name: str):
        """Add image to retraining queue."""
        temp_path = None
        try:
            from azure.storage.blob import BlobServiceClient

            # Convert base64 to jpg
            temp_path = self.base64_to_jpg(base64_image)

            # Get blob service client
            connect_str = ""  # os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if not connect_str:
                logger.error("Azure Storage connection string not found")
                return

            # Upload to blob storage
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            container_name = "retraining-queue"
            container_client = blob_service_client.get_container_client(container_name)

            if not container_client.exists():
                container_client.create_container()

            blob_client = container_client.get_blob_client(f"retraining/{image_name}")

            with open(temp_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            logger.info(f"Added {image_name} to retraining queue")

        except Exception as e:
            logger.error(f"Failed to add to retraining queue: {str(e)}")

        finally:
            # Clean up temporary file
            if temp_path:
                self.delete_jpg(temp_path)

    def process_and_classify_image(
        self, base64_image: str, confidence_threshold: float = 0.60
    ) -> Optional[Dict[str, Any]]:
        """Process and classify a base64 encoded image."""
        try:
            result = self.classify_image(base64_image)
            print(result)

            if result:
                if result["confidence"] < confidence_threshold:
                    logger.warning(f"Low confidence ({result['confidence']}) for image")
                    # self.add_to_retraining_queue(base64_image, image_name)
                else:
                    logger.info(
                        f"Classified image as {result['label']} with confidence {result['confidence']}"
                    )
                return result
            else:
                logger.error(f"Failed to classify image")
                # self.add_to_retraining_queue(base64_image, image_name)
                return None

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            # self.add_to_retraining_queue(base64_image, image_name)
            return None


if __name__ == "__main__":
    # Initialize the service with your Azure Custom Vision credentials
    azure_vision_service(
        VISION_PREDICTION_KEY,
        VISION_PREDICTION_ENDPOINT,
        VISION_PROJECT_ID,
        VISION_ITERATION_NAME,
    )
