import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.db.seed import seed
from app.api.routes import router
from app.ml.predictor import MODEL_PATH
from app.ml.train import main as train_model

app = FastAPI(title=settings.app_name, version="1.1.0", description="Reference capstone implementation for UAV operational analytics and AI-assisted decision support")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    if not os.path.exists(MODEL_PATH):
        train_model()
    seed()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "DroneOptAI",
        "version": "1.1.0",
        "database": "postgresql" if settings.database_url.startswith("postgres") else "sqlite",
        "model_ready": os.path.exists(MODEL_PATH),
    }
