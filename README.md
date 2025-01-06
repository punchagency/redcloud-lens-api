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
   git clone https://github.com/RedCloudTechnology/redcloud-lens-api.git
   cd redcloud-lens-api
   ```

2. **Install Dependencies**
   Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Database**
   Create and update the `.env` with your MySQL credentials:
   ```text
    DB_USERNAME=****
    DB_PASSWORD=****
    DB_HOST=****
    DB_NAME=****
    OPENAI_API_KEY=****
   ```

4. **Run the API**
   Start the FastAPI server:
   ```bash
   uvicorn app:app --reload
   ```

5. **Test the API**
   Use a tool like `curl` or Postman to send a POST request:
   ```bash
   curl -X POST http://127.0.0.1:8000/nlq -H "Content-Type: application/json" -d '{"query": "Cheap Samsung Phones"}'
   ```

---

#### **Usage**

- **Training the Model**:  
  Use `train_model.py` to train the Flair NER model with your data.
  
- **Testing the Model**:  
  Use `test_model.py` to test the Flair model on new sentences.

- **API Endpoints**:
  - **`POST /nlq`**:
    - Input: A JSON payload with a natural language query.
    - Output: Query results from the `Products` table.

---

#### **Example Request**
**Input**:
```json
{
    "query": "Cheap Samsung Phones"
}
```

**Output**:
```json
{
    "query": "Cheap Samsung Phones",
    "results": [
        {
            "ProductID": 1,
            "CategoryName": "Electronics",
            "Brand": "Samsung",
            "ProductName": "Galaxy S21",
            "ProductPrice": 799.99
        }
    ]
}
```

---

#### **Future Improvements**
- Add support for advanced queries (e.g., price ranges or stock availability).
- Enhance NER model performance with additional domain-specific data.
- Integrate user authentication for secure access to API endpoints.

---

#### **Contributors**
- **Your Name**: Developer
- **Additional Contributors**: (List contributors here)

---

#### **License**
This project is licensed under the [MIT License](LICENSE).

---
