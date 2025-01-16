### **Project: RedCloud Lens Natural Language Query API**

---

#### **Overview**
This project implements a FastAPI-based RESTful API for querying an e-commerce product database using natural language queries (NLQ). It uses a gpt-4o model to extract entities like `CategoryName`, `Brand`, and `ProductName` from natural language input, dynamically converts them to SQL queries, and retrieves relevant results from a MySQL database.

---

#### **Features**
- Parse natural language queries to extract entities using a gpt-4o model.
- Dynamically construct SQL queries to fetch data from a MySQL database.
- Train and test custom NER models tailored to e-commerce product data (coming soon).
- Flexible and modular design for future extensibility.

---

#### **Directory Structure**
```
project/
├── db
│   ├── mongo
│   ├── __pycache__
│   ├── helpers.py
│   ├── __init__.py
│   └── store.py
├── external_services
│   ├── __pycache__
│   ├── azure_vision.py
│   ├── __init__.py
│   └── vertex.py
├── nginx
│   └── nginx.conf
├── resources
│   ├── data
│   │   └── train.txt
│   └── taggers
│       └── ecommerce-ner
├── routers
│   ├── categories
│   │   ├── __pycache__
│   │   ├── category_router.py
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── nlq
│   │   ├── __pycache__
│   │   ├── helpers.py
│   │   ├── __init__.py
│   │   ├── nlq_router.py
│   │   └── schemas.py
│   ├── __pycache__
│   └── __init__.py
├── temp_images
├── tests
│   ├── __pycache__
│   ├── constants.py
│   ├── __init__.py
│   ├── mexican_coke.jpg
│   ├── test_nlq_api_edge_cases.py
│   └── test_nlq_api.py
├── app.py
├── CONTRIBUTING.md
├── db.py
├── DEPLOYMENT.md
├── deploy.sh
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.dev
├── Dockerfile.prod
├── gunicorn_config.py
├── __init__.py
├── Procfile
├── README.md
├── requirements.prod.txt
├── requirements.txt
├── settings.py
├── start_app.sh
└── start_tests.sh

```

---

#### **Setup Instructions**

1. **Clone the Repository**
   ```bash
   git clone https://github.com/punchagency/redcloud-lens-api.git
   cd redcloud-lens-api
   ```

2. **Install Dependencies**
   Create a virtual environment and install the required Python libraries:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Database**
   Create and update the `.env` with your necessary credentials:
   ```text
      DB_USERNAME=****
      DB_PASSWORD=****
      DB_HOST=****
      DB_NAME=****
      OPENAI_API_KEY=****
      GCP_PROJECT_ID=****
      INFERENCE_API_TOKEN=****
      GCP_AUTH_TOKEN=****
      GCP_API_KEY=****
      VISION_PREDICTION_KEY=****
      VISION_PREDICTION_ENDPOINT=****
      VISION_PROJECT_ID=****
      VISION_ITERATION_NAME=****
      APP_ENV=dev
   ```

4. **Run the API**
   Start the FastAPI server:
   ```bash
   source start_app.sh
   ```

5. **Test the API**
   Use a tool like `curl` or Postman to send a POST request. 
   You can also visit the swagger UI at `http://127.0.0.1:8000/docs` to test the API.

---

#### **Future Improvements**
- Add support for advanced queries (e.g., price ranges or stock availability).
- Integrate user authentication for secure access to API endpoints.

---

#### **Contributors**
- **Your Name**: Developer
- **Additional Contributors**: (List contributors here)

---

#### **License**
This project is licensed under the [MIT License](LICENSE).

---
