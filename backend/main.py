from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from db.session import engine
from db.base import Base
from investigation.routes import router as investigations_router
from evidence.routes import router as evidence_router
from api.routes import router as api_router

import models.investigation
import models.evidence_file
import models.event
import models.entity
import models.relationship
import models.note
import models.flagged_event

app = FastAPI(title="BlackBox", version="0.1.0", description="Evidence-driven event reconstruction platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(investigations_router, prefix="/api/investigations", tags=["investigations"])
app.include_router(evidence_router, prefix="/api/investigations", tags=["evidence"])
app.include_router(api_router, prefix="/api/investigations", tags=["api"])

os.makedirs("uploads", exist_ok=True)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/api/health")
async def health():
    return {"status": "ok"}
