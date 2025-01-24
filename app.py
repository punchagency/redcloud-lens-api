import datetime
import json
import logging
import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console
from rich.logging import RichHandler

from db.store import initialize_database
from routers.categories import category_router
from routers.nlq import nlq_router
from settings import get_settings

settings = get_settings()


class StructuredLogger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        if extra is None:
            extra = {}
        extra["app_name"] = "Red Lens API Service"
        # Truncate large payloads to avoid excessive logging
        max_payload_size = 1024
        if isinstance(msg, dict):
            msg = json.dumps(msg, indent=4)
        if len(msg) > max_payload_size:
            msg = msg[:max_payload_size] + "..."
        super()._log(level, msg, args, exc_info, extra, stack_info)


# Initialize a Rich console
console = Console()

# Configure the logger with RichHandler
handler = RichHandler(console=console, rich_tracebacks=True)
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logging.setLoggerClass(StructuredLogger)


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


@app.middleware("http")
async def log_structured_requests(request: Request, call_next):
    start_time = datetime.datetime.now()

    if settings.APP_ENV == "dev":
        from pyinstrument import Profiler
        # Start the profiler
        profiler = Profiler()
        profiler.start()

    try:
        logger.info(
            {
                "event": "request",
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client": request.client.host,
                "body": await request.body(),
            }
        )
        response: Response = await call_next(request)
    finally:
        if settings.APP_ENV == "dev":
            # Stop the profiler
            profiler.stop()

            # Save the profiling results to a file
            output_dir = "profiling_reports"
            os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
            report_file = os.path.join(
                output_dir,
                f"profile_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            )

            # Write the profiler's HTML output to the file
            with open(report_file, "w") as f:
                f.write(profiler.output_html())

            logger.info(f"Profiling results saved to: {report_file}")

    processing_time = (datetime.datetime.now() - start_time).total_seconds()
    logger.info(
        {
            "event": "response",
            "status_code": response.status_code,
            "processing_time": processing_time,
        }
    )
    return response


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
