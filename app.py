import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.store import initialize_database
from routers.categories import category_router
from routers.nlq import nlq_router


db_file = "conversations.db"  # Ensure this matches your DATABASE_URL
if not os.path.exists(db_file):
    print(f"Database file '{db_file}' not found. Creating a new instance...")
    initialize_database()
else:
    print(f"Database file '{db_file}' already exists.")


# FastAPI App Configuration
app = FastAPI(
    swagger_ui_parameters={"syntaxHighlight": False},
    title="RedCloud Lens Natural Lang Query API",
    description="RedCloud Lens Natural Lang Query API helps you do awesome stuff. 🚀",
    summary="Deadpool's favorite app. Nuff said.",
    version="0.0.2",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "RedCloud Lens Natural Lang Query API",
        "url": "http://x-force.example.com/contact/",
        "email": "dp@x-force.example.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include router
app.include_router(nlq_router.router, prefix="/api")
app.include_router(category_router.router, prefix="/api")
