import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models.investigation import Investigation
from schemas.investigation import InvestigationCreate, InvestigationUpdate, InvestigationOut

router = APIRouter()

@router.post("/", response_model=InvestigationOut, status_code=201)
async def create_investigation(
    payload: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
    x_user_email: Optional[str] = Header(default=None),
):
    inv = Investigation(**payload.model_dump(), owner_email=x_user_email)
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv

@router.get("/", response_model=list[InvestigationOut])
async def list_investigations(
    db: AsyncSession = Depends(get_db),
    x_user_email: Optional[str] = Header(default=None),
):
    q = select(Investigation).order_by(Investigation.created_at.desc())
    if x_user_email:
        q = q.where(Investigation.owner_email == x_user_email)
    result = await db.execute(q)
    return result.scalars().all()

@router.get("/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    return inv

@router.patch("/{investigation_id}", response_model=InvestigationOut)
async def update_investigation(investigation_id: uuid.UUID, payload: InvestigationUpdate, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(inv, k, v)
    await db.commit()
    await db.refresh(inv)
    return inv

@router.delete("/{investigation_id}", status_code=204)
async def delete_investigation(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    await db.delete(inv)
    await db.commit()
