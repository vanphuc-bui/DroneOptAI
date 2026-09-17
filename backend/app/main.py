from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.db.seed import seed
from app.api.routes import router

app=FastAPI(title=settings.app_name, version="1.0.0", description="Reference capstone implementation for UAV operational analytics and AI-assisted decision support")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    seed()

@app.get("/health")
def health(): return {"status":"ok","service":"DroneOptAI"}
