from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ward
from ..schemas import WardIn, WardPatch

router = APIRouter(prefix="/wards", tags=["wards"])


def _o(w):
    return {"id": w.id, "code": w.code, "name": w.name, "active": w.active}


@router.get("")
def list_wards(db: Session = Depends(get_db)):
    return [_o(w) for w in db.scalars(select(Ward).order_by(Ward.code))]


@router.post("", status_code=201)
def create_ward(p: WardIn, db: Session = Depends(get_db)):
    if db.scalar(select(Ward).where(Ward.code == p.code)):
        raise HTTPException(409, "Ward code already exists")
    w = Ward(code=p.code, name=p.name.strip())
    db.add(w)
    db.commit()
    return _o(w)


@router.patch("/{ward_id}")
def patch_ward(ward_id: int, p: WardPatch, db: Session = Depends(get_db)):
    w = db.get(Ward, ward_id)
    if not w:
        raise HTTPException(404, "Ward not found")
    if p.name is not None:
        w.name = p.name.strip()
    if p.active is not None:
        w.active = p.active
    db.commit()
    return _o(w)
