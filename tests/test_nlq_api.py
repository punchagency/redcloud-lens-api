import pytest
from fastapi.testclient import TestClient

from app import app
from tests.constants import image_to_base64  # Import your FastAPI app instance

client = TestClient(app)

BASE_64_IMG = image_to_base64("tests/mexican_coke.jpg")


@pytest.fixture
def valid_request_body():
    return {
        "query": "Find products cheaper than $10",
        "product_image": None,
    }


# Test Cases


def test_nlq_success_with_query(valid_request_body):
    """
    Test the endpoint with a valid natural language query.
    """
    response = client.post("/api/nlq", json=valid_request_body)
    assert response.status_code == 200
    json_response = response.json()
    assert "query" in json_response
    assert "results" in json_response
    assert isinstance(json_response["results"], list)


def test_nlq_success_with_image(valid_request_body):
    """
    Test the endpoint with a valid product image (base64 string).
    """
    valid_request_body["query"] = None
    valid_request_body["product_image"] = (
        BASE_64_IMG  # Replace with an actual base64 string
    )

    response = client.post("/api/nlq", json=valid_request_body)
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


def test_nlq_missing_query_and_image():
    """
    Test the endpoint with a request missing both query and product_image.
    """
    response = client.post("/api/nlq", json={"query": None, "product_image": None})
    assert response.status_code == 400
    assert response.json()["detail"] == "No image or query submitted."


def test_nlq_no_limit_parameter(valid_request_body):
    """
    Test the endpoint without providing a limit parameter.
    """
    response = client.post("/api/nlq", json=valid_request_body)
    assert response.status_code == 200
    json_response = response.json()
    assert "query" in json_response
    assert "results" in json_response


def test_nlq_large_limit(valid_request_body):
    """
    Test the endpoint with a very large limit parameter.
    """
    response = client.post("/api/nlq?limit=1000000", json=valid_request_body)
    assert response.status_code == 200
    json_response = response.json()
    assert "query" in json_response
    assert "results" in json_response
    assert isinstance(json_response["results"], list)
