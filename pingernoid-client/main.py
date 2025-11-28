from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from typing import Annotated
from uuid import UUID

from .database import create_db_and_tables, SessionDep
from .crud import PingerRepository
from .service import PingerService
from .models import Result, Target, TargetBase

# --- Dependency Chain Setup ---


def get_pinger_repo(session: SessionDep) -> PingerRepository:
    """Dependency that injects the database session into the Repository."""
    return PingerRepository(session=session)


PingerRepoDep = Annotated[PingerRepository, Depends(get_pinger_repo)]


def get_pinger_service(repo: PingerRepoDep) -> PingerService:
    """Dependency that injects the Repository into the Service."""
    return PingerService(repo=repo)


PingerServiceDep = Annotated[PingerService, Depends(get_pinger_service)]


app = FastAPI(title="Pingernoid API", description="A microservice for persistent ICMP monitoring.")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# --- Target Endpoints ---


@app.get("/targets/", response_model=list[Target])
def get_targets(service: PingerServiceDep) -> list[Target]:
    return service.repo.get_all_targets()


@app.get("/target/{target_id}", response_model=Target)
def get_target(target_id: UUID, service: PingerServiceDep) -> Target:
    target = service.repo.get_target_by_id(target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target with ID {target_id} not found.")
    return target


@app.post("/target/", response_model=Target)
def create_target(target: TargetBase, service: PingerServiceDep, background_tasks: BackgroundTasks) -> Target:
    existing_target = service.repo.get_target_by_ip(target.ip_addr)
    if existing_target:
        raise HTTPException(status_code=409, detail=f"Target with IP address {target.ip_addr} already exists.")

    db_target = service.repo.create_target(target)

    # 💡 Use the Service method for background task
    background_tasks.add_task(service.ping_target, db_target)

    return db_target


@app.put("/target/{target_id}", response_model=Target)
def update_target(target_id: UUID, target_data: TargetBase, service: PingerServiceDep) -> Target:
    updated_target = service.repo.update_target(target_id, target_data)
    if not updated_target:
        raise HTTPException(status_code=404, detail=f"Target with ID {target_id} not found.")
    return updated_target


@app.delete("/target/{target_id}")
def delete_target(target_id: UUID, service: PingerServiceDep) -> dict:
    if not service.repo.delete_target(target_id):
        raise HTTPException(status_code=404, detail=f"Target with ID {target_id} not found.")
    return {"message": f"Target with ID {target_id} was deleted successfully!"}


# --- Results/Monitor Endpoints ---


@app.get("/results/", response_model=list[Result])
def get_results(service: PingerServiceDep) -> list[Result]:
    return service.repo.get_all_results()


@app.get("/result/{result_id}", response_model=Result)
def get_result(result_id: UUID, service: PingerServiceDep) -> Target:
    result = service.repo.get_result_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Result with ID {result} not found.")
    return result


@app.get("/monitor/{target_id}", response_model=list[Result])
def get_monitor(target_id: UUID, service: PingerServiceDep, background_tasks: BackgroundTasks) -> list[Result]:
    target = service.repo.get_target_by_id(target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target with ID {target_id} not found.")

    # Trigger the background ping using the service method
    background_tasks.add_task(service.ping_target, target)

    # Get all results for this target's IP
    results = service.repo.get_results_by_ip(target.ip_addr)
    return results
