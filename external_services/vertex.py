import base64
import io
import os
import sys
import time

import PIL
import PIL.Image
from google.cloud import aiplatform, storage
from google.cloud.aiplatform.gapic import PredictionServiceClient
from google.cloud.aiplatform.gapic.schema import predict
from loguru import logger
from PIL import Image

# f"https://ENDPOINT_ID.LOCATION_ID-PROJECT_NUMBER.prediction.vertexai.goog/v1/projects/PROJECT_NUMBER/locations/LOCATION_ID/endpoints/ENDPOINT_ID:predict"


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
    "vertex_ai_service.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="1 week",
)

# Set the environment variable for authentication
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
#     "../mimetic-maxim-443710-s2-d6ddbd185ca2.json"
# )


ENDPOINT_ID = "6184711124798144512"
PROJECT_ID = "225990659434"
LOCATION = "europe-west4"

# Initialize AI Platform client
aiplatform.init(project=PROJECT_ID, location=LOCATION)


class VertexAIService:
    """
    A service to interact with Google Vertex AI for image classification tasks.
    This service supports image classification from  base64 encoded images.
    It also handles failed predictions by adding images to the retraining queue on Google Cloud Storage.
    """

    def __init__(
        self, project_id: str, endpoint_id: str, location: str = "europe-west4"
    ):
        """
        Initializes the VertexAIService with project details and AI platform endpoint.

        :param project_id: The Google Cloud project ID.
        :param endpoint_id: The ID of the deployed Vertex AI endpoint.
        :param location: The location where the model is deployed (default: "us-central1").
        """

        self.project_id = project_id
        self.endpoint_id = endpoint_id
        self.location = location

        # projects/225990659434/locations/europe-west4/endpoints/6184711124798144512

        # The endpoint for Vertex AI predictions
        self.endpoint = "europe-west4-aiplatform.googleapis.com"

        # Client options to set the API endpoint region
        client_options = {"api_endpoint": self.endpoint}

        # Initialize the Prediction client with the custom API endpoint
        self.client = aiplatform.gapic.PredictionServiceClient(
            client_options=client_options
        )

    def encode_image_to_base64(self, image: Image) -> str:
        """
        Convert a PIL image to a base64 encoded string.

        :param image: A PIL Image object to be converted.
        :return: A base64 encoded string representing the image.
        """
        try:
            # Convert PIL Image to byte array
            img_byte_arr = io.BytesIO()
            image.save(
                img_byte_arr, format="JPEG"
            )  # Can also save as PNG or other formats
            img_byte_arr = img_byte_arr.getvalue()

            # Convert byte array to base64 string
            base64_str = base64.b64encode(img_byte_arr).decode("utf-8")

            return base64_str
        except Exception as e:
            logger.error(f"Failed to encode image to base64: {str(e)}")
            return None

    def classify_image(self, image: str) -> dict:
        """
        Classifies an image using the Google Vertex AI model deployed at the specified endpoint.
        :param image: A PIL Image object to be classified.
        :return: A dictionary containing the predicted label and confidence score, or None if an error occurs.
        """
        try:
            # # Ensure the image is in PIL format
            # if not isinstance(image, Image.Image):
            #     logger.error("Input is not a valid PIL image.")
            #     return None

            # # Convert the image to base64
            # encoded_image = self.encode_image_to_base64(image)
            # if not encoded_image:
            #     logger.error("Image encoding failed.")
            #     return None
            encoded_image = image

            # Prepare the instances for prediction (Google Vertex AI expects base64 encoded images)
            instance = predict.instance.ImageClassificationPredictionInstance(
                content=encoded_image
            ).to_value()

            instances = [instance]

            # Set the prediction parameters (confidence threshold, max predictions, etc.)
            parameters = predict.params.ImageClassificationPredictionParams(
                confidence_threshold=0.75, max_predictions=5
            ).to_value()

            # make the prediction request to the vertex ai endpoint
            endpoint = self.client.endpoint_path(
                project=self.project_id,
                location=self.location,
                endpoint=self.endpoint_id,
            )

            response = self.client.predict(
                endpoint=endpoint, instances=instances, parameters=parameters
            )

            # Log the response
            logger.info(f"Prediction response: {response.predictions}")

            # Process the predictions
            predictions = response.predictions

            print("length", len(predictions))

            if predictions:
                # Extract and return the first prediction (most probable result)
                prediction = predictions[0]
                label = prediction.get("displayNames", ["Unknown"])[0]
                confidence = prediction.get("confidences", [0.0])[
                    0
                ]  # Extract confidence
                return {"label": label, "confidence": confidence}

            logger.warning("No predictions returned.")
            return None
        except Exception as e:
            logger.error(f"Error during image classification: {str(e)}")
            return None

    def add_to_retraining_queue(self, image_path: str, image_name: str):
        """
        Uploads failed images to Google Cloud Storage (GCS) for manual labeling by labellers.
        :param image_path: The local file path of the image.
        :param image_name: The name of the image.
        """
        try:
            logger.info(f"Adding {image_name} to retraining queue.")

            # Set the GCS bucket name (replace with your actual bucket)
            bucket_name = "redlens_bucket"
            client = storage.Client()
            bucket = client.get_bucket(bucket_name)

            # Create a blob for the image in the 'retraining/' directory
            blob = bucket.blob(f"retraining/{image_name}")

            # Upload the image to GCS
            with open(image_path, "rb") as img_data:
                blob.upload_from_file(img_data)

            logger.info(f"Image {image_name} uploaded to retraining queue.")

        except Exception as e:
            logger.error(f"Failed to upload {image_name} to retraining queue: {str(e)}")

    def process_and_classify_image(
        self, pil_image: str, image_name: str, confidence_threshold: float = 0.75
    ):
        """
        Processes an image: classifies it and handles failed predictions by adding them to the retraining queue.
        :param pil_image: The PIL image to be classified.
        :param image_name: The name of the image.
        :param confidence_threshold: The minimum confidence score to consider the prediction valid.
        """
        try:
            # Classify the image using Vertex AI
            result = self.classify_image(pil_image)

            if result:
                # Check if the confidence score is below the threshold
                if result["confidence"] < confidence_threshold:
                    logger.warning(
                        f"Prediction confidence ({result['confidence']}) is below threshold for image {image_name}."
                    )
                    # If confidence is too low, add the image to the retraining queue
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
                # # If classification fails, add the image to the retraining queue
                self.add_to_retraining_queue(image_name, image_name)
                return None
        except Exception as e:
            logger.error(f"Error processing image {image_name}: {str(e)}")
            # If an error occurs, add the image to the retraining queue
            self.add_to_retraining_queue(image_path, image_name)


# Example usage
if __name__ == "__main__":
    # Initialize the service with your project ID and endpoint ID
    service = VertexAIService(project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID)

    # Example image to process
    image_path = "../7up.jpg"
    image = PIL.Image.open(image_path)
    # image_name = "sample_image.jpg"

    # Process and classify the example image
    service.process_and_classify_image(image, image_path)
