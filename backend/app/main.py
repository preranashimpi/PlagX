
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes.compare import router as compare_router
from app.routes.upload import router as upload_router
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PlagX API",
    description="Multilingual Plagiarism Detection System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(compare_router)
@app.get("/")
def home():
    return {
        "message": "Welcome to PlagX API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "project": "PlagX"
    }
