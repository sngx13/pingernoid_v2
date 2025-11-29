from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from uuid import UUID
from typing import Annotated
from pingernoid_client.db.crud import PingerRepository
from pingernoid_client.db.models import Result
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

# --- Monitor Endpoints ---


@router.get("/monitor/{target_id}", response_model=list[Result])
def get_monitor(target_id: UUID, service: PingerServiceDep, background_tasks: BackgroundTasks) -> list[Result]:
    target = service.repo.get_target_by_id(target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target with ID {target_id} not found.")

    # Trigger the background ping using the service method
    background_tasks.add_task(service.ping_target, target)

    # Get all results for this target's IP
    results = service.repo.get_results_by_ip(target.ip_addr)
    return results
