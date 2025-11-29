from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import Annotated
from pingernoid_client.db.crud import PingerRepository
from pingernoid_client.db.models import Target, Result
from pingernoid_client.service import PingerService
from pingernoid_client.db.database import SessionDep


router = APIRouter()


def get_pinger_repo(session: SessionDep) -> PingerRepository:
    """Dependency that injects the database session into the Repository."""
    return PingerRepository(session=session)


PingerRepoDep = Annotated[PingerRepository, Depends(get_pinger_repo)]


def get_pinger_service(repo: PingerRepoDep) -> PingerService:
    """Dependency that injects the Repository into the Service."""
    return PingerService(repo=repo)


PingerServiceDep = Annotated[PingerService, Depends(get_pinger_service)]

# --- Results Endpoints ---


@router.get("/results/", response_model=list[Result])
def get_results(service: PingerServiceDep) -> list[Result]:
    return service.repo.get_all_results()


@router.get("/result/{result_id}", response_model=Result)
def get_result(result_id: UUID, service: PingerServiceDep) -> Target:
    result = service.repo.get_result_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Result with ID {result} not found.")
    return result
