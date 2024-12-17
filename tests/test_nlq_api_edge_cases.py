from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app import app
from tests.constants import image_to_base64

load_dotenv()

client = TestClient(app, base_url="http://127.0.0.1:8000")

BASE_64_IMG = image_to_base64("tests/mexican_coke.jpg")


# Fixtures for mock objects
@pytest.fixture
def mock_bigquery_client():
    with patch("routers.nlq.nlq_router.bigquery.Client") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_helpers():
    with patch(
        "routers.nlq.nlq_router.process_product_image", return_value="processed_image"
    ) as mock_process:
        with patch(
            "routers.nlq.nlq_router.detect_text",
            return_value={"responses": [{"fullTextAnnotation": {"text": "coke"}}]},
        ):
            with patch(
                "routers.nlq.nlq_router.request_image_inference",
                return_value={"label": "coke"},
            ):
                with patch(
                    "routers.nlq.nlq_router.parse_query",
                    return_value="SELECT * FROM marketplace_product_nigeria LIMIT 10",
                ):
                    yield {
                        "mock_process_product_image": mock_process,
                        "mock_detect_text": mock_process,
                        "mock_request_inference": mock_process,
                    }


@pytest.fixture
def valid_request_body():
    return {
        "query": "Find products cheaper than $10",
        "product_image": None,
    }


# Test Cases


def test_nlq_success_with_query(mock_bigquery_client, mock_helpers, valid_request_body):
    """
    Test the endpoint with a valid natural language query.
    """
    response = client.post("/api/nlq", json=valid_request_body)
    assert response.status_code == 200
    json_response = response.json()
    assert "query" in json_response
    assert "results" in json_response
    assert isinstance(json_response["results"], list)


def test_nlq_success_with_image(mock_bigquery_client, mock_helpers):
    """
    Test the endpoint with a valid product image.
    """
    response = client.post(
        "/api/nlq",
        json={"query": None, "product_image": BASE_64_IMG},
    )
    assert response.status_code == 200
    json_response = response.json()
    assert "query" in json_response
    assert "results" in json_response
    assert isinstance(json_response["results"], list)


def test_nlq_empty_request():
    """
    Test the endpoint with an empty request body.
    """
    response = client.post("/api/nlq", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "No image or query submitted."


def test_nlq_invalid_limit():
    """
    Test the endpoint with an invalid limit parameter.
    """
    response = client.post("/api/nlq?limit=-1", json={"query": "Test"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Limit must be greater than zero."


# def test_nlq_bigquery_error(mock_bigquery_client, mock_helpers):
#     """
#     Test the endpoint when BigQuery encounters an error.
#     """
#     mock_bigquery_client.query.side_effect = Exception("BigQuery error")
#     response = client.post("/api/nlq", json={"query": "Test"})
#     assert response.status_code == 500
#     assert "BigQuery error" in response.json()["detail"]


def test_nlq_image_inference_failure(mock_helpers):
    """
    Test the endpoint when image inference fails.
    """
    with patch(
        "routers.nlq.nlq_router.request_image_inference",
        side_effect=Exception("Inference failed"),
    ):
        response = client.post("/api/nlq", json={"product_image": "BASE_64_IMG"})
        assert response.status_code == 200
        assert "query" in response.json()
        assert "results" in response.json()


def test_nlq_query_parsing_failure(mock_helpers):
    """
    Test the endpoint when query parsing fails.
    """
    with patch("routers.nlq.nlq_router.parse_query", return_value=None):
        response = client.post(
            "/api/nlq", json={"query": "products cheaper than 10 bucks"}
        )
        assert response.status_code == 400
        assert "No valid filters identified from query." in response.json()["detail"]


def test_nlq_detect_text_called(mock_helpers):
    """
    Test that detect_text is called when processing an image.
    """
    response = client.post("/api/nlq", json={"product_image": BASE_64_IMG})
    assert response.status_code == 200
    mock_helpers["mock_detect_text"].assert_called_once()


def test_nlq_process_product_image_called(mock_helpers):
    """
    Test that process_product_image is called when an image is provided.
    """
    response = client.post("/api/nlq", json={"product_image": BASE_64_IMG})
    assert response.status_code == 200
    mock_helpers["mock_process_product_image"].assert_called_once()
