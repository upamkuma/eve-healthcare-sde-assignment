from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_admin
from app.core.cache import cache_manager
from app.db.session import get_db
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest
from app.models.user import User
from app.schemas.diagnostic import (
    CentreCreate,
    CentreResponse,
    CentreUpdate,
    TestCreate,
    TestResponse,
    TestUpdate,
)

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.get("", response_model=list[CentreResponse])
def list_centres(
    search: str | None = Query(default=None, description="Search by centre name or location"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    cache_key = f"centres:list:{search}:{page}:{page_size}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached

    query = db.query(DiagnosticCentre).options(selectinload(DiagnosticCentre.tests))

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (DiagnosticCentre.name.ilike(search_pattern))
            | (DiagnosticCentre.location.ilike(search_pattern))
        )

    offset = (page - 1) * page_size
    results = query.order_by(DiagnosticCentre.id).offset(offset).limit(page_size).all()

    # Convert to response objects
    response_data = [CentreResponse.model_validate(c).model_dump(mode="json") for c in results]
    cache_manager.set(cache_key, response_data, ttl_seconds=60)
    return results


@router.get("/{centre_id}", response_model=CentreResponse)
def get_centre(centre_id: int, db: Session = Depends(get_db)):
    cache_key = f"centres:{centre_id}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached

    centre = (
        db.query(DiagnosticCentre)
        .options(selectinload(DiagnosticCentre.tests))
        .filter(DiagnosticCentre.id == centre_id)
        .first()
    )
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    cache_manager.set(
        cache_key,
        CentreResponse.model_validate(centre).model_dump(mode="json"),
        ttl_seconds=60,
    )
    return centre


@router.post("", response_model=CentreResponse, status_code=status.HTTP_201_CREATED)
def create_centre(
    payload: CentreCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    centre = DiagnosticCentre(name=payload.name.strip(), location=payload.location.strip())
    db.add(centre)
    db.commit()
    db.refresh(centre)
    cache_manager.invalidate_all()
    return centre


@router.put("/{centre_id}", response_model=CentreResponse)
def update_centre(
    centre_id: int,
    payload: CentreUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    if payload.name is not None:
        centre.name = payload.name.strip()
    if payload.location is not None:
        centre.location = payload.location.strip()

    db.commit()
    db.refresh(centre)
    cache_manager.invalidate_all()
    return centre


@router.delete("/{centre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_centre(
    centre_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    db.delete(centre)
    db.commit()
    cache_manager.invalidate_all()
    return None


@router.get("/{centre_id}/tests", response_model=list[TestResponse])
def list_centre_tests(
    centre_id: int,
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    query = db.query(DiagnosticTest).filter(DiagnosticTest.centre_id == centre_id)
    if search:
        query = query.filter(DiagnosticTest.name.ilike(f"%{search.strip()}%"))

    return query.order_by(DiagnosticTest.id).all()


@router.get("/{centre_id}/tests/{test_id}", response_model=TestResponse)
def get_centre_test(centre_id: int, test_id: int, db: Session = Depends(get_db)):
    test = (
        db.query(DiagnosticTest)
        .filter(DiagnosticTest.id == test_id, DiagnosticTest.centre_id == centre_id)
        .first()
    )
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found at this centre")
    return test


@router.post(
    "/{centre_id}/tests",
    response_model=TestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test(
    centre_id: int,
    payload: TestCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    test = DiagnosticTest(
        centre_id=centre.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        price=payload.price,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    cache_manager.invalidate_all()
    return test


@router.put("/{centre_id}/tests/{test_id}", response_model=TestResponse)
def update_test(
    centre_id: int,
    test_id: int,
    payload: TestUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    test = (
        db.query(DiagnosticTest)
        .filter(DiagnosticTest.id == test_id, DiagnosticTest.centre_id == centre_id)
        .first()
    )
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found at this centre")

    if payload.name is not None:
        test.name = payload.name.strip()
    if payload.description is not None:
        test.description = payload.description.strip()
    if payload.price is not None:
        test.price = payload.price

    db.commit()
    db.refresh(test)
    cache_manager.invalidate_all()
    return test


@router.delete("/{centre_id}/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test(
    centre_id: int,
    test_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    test = (
        db.query(DiagnosticTest)
        .filter(DiagnosticTest.id == test_id, DiagnosticTest.centre_id == centre_id)
        .first()
    )
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found at this centre")

    db.delete(test)
    db.commit()
    cache_manager.invalidate_all()
    return None
