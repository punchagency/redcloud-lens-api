### **Project: RedCloud Lens Natural Language Query API**

---

#### **Overview**
This project implements a FastAPI-based RESTful API for querying an e-commerce product database using natural language queries (NLQ). It uses a custom-trained Flair NER model to extract entities like `CategoryName`, `Brand`, and `ProductName` from natural language input, dynamically converts them to SQL queries, and retrieves relevant results from a MySQL database.

---

#### **Features**
- Parse natural language queries to extract entities using a Flair NER model.
- Dynamically construct SQL queries to fetch data from a MySQL database.
- Train and test custom NER models tailored to e-commerce product data.
- Flexible and modular design for future extensibility.

---

#### **Directory Structure**
```
project/
│
├── app.py                      # FastAPI application
├── train_model.py              # Script to train the Flair NER model
├── test_model.py               # Script to test the Flair NER model
├── resources/                  # Folder for models and data
│   ├── taggers/
│   │   └── ecommerce-ner/      # Folder for the trained Flair model
│   └── data/                   # Folder for training and test data
│       ├── train.txt           # Training data in BIO format
│       ├── test.txt            # Test data in BIO format
│       └── dev.txt             # Validation data in BIO format
└── requirements.txt            # Python dependencies
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
   ```

4. **Train the Flair Model**
   Train a custom Flair NER model using your labeled e-commerce data:
   ```bash
   python train_model.py
   ```

5. **Run the API**
   Start the FastAPI server:
   ```bash
   uvicorn app:app --reload
   ```

6. **Test the API**
   Use a tool like `curl` or Postman to send a POST request:
   ```bash
   curl -X POST http://127.0.0.1:8000/nlq -H "Content-Type: application/json" -d '{"query": "Find all products in Electronics from Samsung"}'
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
    "query": "Find all products in Electronics from Samsung"
}
```

**Output**:
```json
{
    "query": "Find all products in Electronics from Samsung",
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
