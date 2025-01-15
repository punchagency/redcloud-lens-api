import base64
import io
import sys
from typing import Optional, Dict, Any, Union
from azure.cognitiveservices.vision.customvision.prediction import (
    CustomVisionPredictionClient,
)
from msrest.authentication import ApiKeyCredentials
from PIL import Image
from loguru import logger
import os
import uuid
import requests
from urllib.parse import urlparse
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
# VISION_PREDICTION_KEY = "6V48E35SMe82iANGYug53V5pRsp0XHZY1iyGkkgRL5MfLAAWTOavJQQJ99BAACLArgHXJ3w3AAAIACOGVsrv"
# VISION_PREDICTION_ENDPOINT = (
#     "https://redcloudlens-prediction.cognitiveservices.azure.com/"
# )
# VISION_PROJECT_ID = "e34eec4e-ba2a-4496-b1f9-d23448c44fb5"
# VISION_ITERATION_NAME = "Iteration1"  # "redcloudlens"

# ENVIRONMENT VARIABLES
VISION_PREDICTION_KEY = settings.VISION_PREDICTION_KEY
VISION_PREDICTION_ENDPOINT = settings.VISION_PREDICTION_ENDPOINT
VISION_PROJECT_ID = settings.VISION_PROJECT_ID
VISION_ITERATION_NAME = settings.VISION_ITERATION_NAME


class AzureVisionService:
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
            prediction_key (str): The prediction key from Azure Custom Vision
            endpoint (str): The endpoint URL for your Custom Vision service
            project_id (str): The project ID from Azure Custom Vision
            publish_iteration_name (str): The iteration name to use for predictions
            temp_dir (str): Directory for temporary image storage
        """
        self.project_id = project_id
        self.publish_iteration_name = publish_iteration_name
        self.temp_dir = temp_dir

        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)

        # Initialize the prediction client
        credentials = ApiKeyCredentials(in_headers={"Prediction-key": prediction_key})
        self.predictor = CustomVisionPredictionClient(endpoint, credentials)

    def is_valid_url(self, url: str) -> bool:
        """Check if the provided string is a valid URL."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def download_image_from_url(self, url: str) -> str:
        """Download image from URL and save to temporary file."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Generate temporary file path
            temp_filename = f"{uuid.uuid4()}.jpg"
            temp_path = os.path.join(self.temp_dir, temp_filename)

            # Save image
            with open(temp_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded image from URL to: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Failed to download image from URL: {str(e)}")
            return None

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
            return None

    def delete_jpg(self, file_path: str):
        """Delete the temporary jpg file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")

    def classify_image(
        self, image_input: Union[str, bytes]
    ) -> Optional[Dict[str, Any]]:
        """
        Classify an image using either URL, base64 string, or raw bytes.

        Args:
            image_input (Union[str, bytes]): Either an image URL, base64 encoded string, or raw bytes
        """
        temp_path = None

        try:
            if isinstance(image_input, str):
                if self.is_valid_url(image_input):
                    # Classify directly from URL using Azure's URL endpoint
                    results = self.predictor.classify_image_url(
                        self.project_id,
                        self.publish_iteration_name,
                        {"url": image_input},
                    )
                else:
                    # Assume it's a base64 string
                    temp_path = self.base64_to_jpg(image_input)
                    if not temp_path:
                        return None

                    with open(temp_path, "rb") as image_file:
                        results = self.predictor.classify_image(
                            self.project_id,
                            self.publish_iteration_name,
                            image_file.read(),
                        )
            else:
                # Handle raw bytes
                results = self.predictor.classify_image(
                    self.project_id, self.publish_iteration_name, image_input
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
            # Clean up temporary file if it exists
            if temp_path:
                self.delete_jpg(temp_path)

    def process_and_classify_image(
        self, image_input: Union[str, bytes], confidence_threshold: float = 0.60
    ) -> Optional[Dict[str, Any]]:
        """
        Process and classify an image from either URL, base64 string, or raw bytes.

        Args:
            image_input (Union[str, bytes]): Either an image URL, base64 encoded string, or raw bytes
            confidence_threshold (float): Minimum confidence threshold for classification
        """
        try:
            result = self.classify_image(image_input)

            if result:
                if result["confidence"] < confidence_threshold:
                    logger.warning(f"Low confidence ({result['confidence']}) for image")
                else:
                    logger.info(
                        f"Classified image as {result['label']} with confidence {result['confidence']}"
                    )
                return result
            else:
                logger.error("Failed to classify image")
                return None

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return None


if __name__ == "__main__":
    # Initialize the service with your Azure Custom Vision credentials
    azure_vision_service(
        VISION_PREDICTION_KEY,
        VISION_PREDICTION_ENDPOINT,
        VISION_PROJECT_ID,
        VISION_ITERATION_NAME,
    )


# Example usage
# if __name__ == "__main__":
#     # Initialize the service
#     service = AzureVisionService(
#         prediction_key=VISION_PREDICTION_KEY,
#         endpoint=VISION_PREDICTION_ENDPOINT,
#         project_id=VISION_PROJECT_ID,
#         publish_iteration_name=VISION_ITERATION_NAME,
#     )

#     # Example 1: Classify from local file
#     with open("./chivital-mama-cass.jpg", "rb") as image_file:
#         base64_image = base64.b64encode(image_file.read()).decode("utf-8")
#         result = service.process_and_classify_image(base64_image)
#         if result:
#             print(f"Classification result from base64: {result}")

#     # Example 2: Classify from URL
#     image_url = "https://example.com/image.jpg"
#     result = service.process_and_classify_image(image_url)
#     if result:
#         print(f"Classification result from URL: {result}")
