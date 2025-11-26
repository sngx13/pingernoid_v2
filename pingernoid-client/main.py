import re
import subprocess
from datetime import datetime
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from sqlmodel import Field, Session, SQLModel, String, create_engine, select
from typing import Annotated
from uuid import uuid4, UUID

from .models import Result, Target, TargetBase


sqlite_file_name = "pingernoid.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


def add_result(result: Result, session: SessionDep):
    print(f"=> Writing ping results to database for: {result.ip_addr}")
    try:
        session.add(result)
        session.commit()
        session.refresh(result)
        print(f"=> Successfully wrote result {result.id} to database.")
    except Exception as e:
        print(f"=> Failed to write result for {result.ip_addr} to database: {e}")


def parse_ping_output(ip_addr: str, output: str) -> Result | None:
    pattern = re.compile(
        r"(\d+)\s+packets\s+transmitted,\s+(\d+)\s+packets\s+received.*?(\d+\.\d+)%\s+packet\s+loss.*?(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(output)
    if match:
        result = Result(
            ip_addr=ip_addr,
            timestamp=datetime.now(),
            sent=int(match.group(1)),
            rcvd=int(match.group(2)),
            loss=float(match.group(3)),
            rtt_min=float(match.group(4)),
            rtt_avg=float(match.group(5)),
            rtt_max=float(match.group(6)),
        )
    return result


def ready_to_ping(target: TargetBase, session: SessionDep) -> bool:
    print(f"=> Checking whether interval has passed before performing next ICMP test...")
    time_now = datetime.now().replace(microsecond=0)
    previous_result_timestamp = session.exec(select(Result.timestamp).where(Result.ip_addr == target.ip_addr)).all()
    if previous_result_timestamp:
        elapsed_time = time_now - previous_result_timestamp[0]
        if elapsed_time.total_seconds() < target.interval:
            print(
                f"=> Not enough time has passed since last ICMP test towards the target: {target.ip_addr}, remaining: {target.interval - elapsed_time.total_seconds()} seconds..."
            )
            return False
        else:
            print(f"=> Time has passed since last ICMP test: {elapsed_time} towards the target: {target.ip_addr}")
            return True
    else:
        print(f"=> Unable to find previous ICMP tests for the target: {target.ip_addr}")
        return True


def ping_target(target: Target, session: SessionDep):
    print(f"=> Attempting to send ICMP probes to: {target.ip_addr}")
    if ready_to_ping(target, session):
        try:
            cmd = [
                "ping",
                "-c",
                str(target.count),
                "-t",
                str(target.timeout),
                "-s",
                str(target.size),
                "-i",
                str(target.wait),
                str(target.ip_addr),
            ]
            cmd_output = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=target.timeout + 10)
            print(f"=> ICMP output:\n{cmd_output.stdout}")
            parsed_result = parse_ping_output(target.ip_addr, cmd_output.stdout)
            if parsed_result:
                add_result(parsed_result, session)
            else:
                print(f"=> Failed to parse ping output for {target.ip_addr}")
        except print.CalledProcessError as e:
            print(f"=> Ping failed for {target.ip_addr}: Return Code {e.returncode}. Stderr: {e.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"=> Ping command timed out for {target.ip_addr} after {target.timeout + 10} seconds.")
        except Exception as e:
            print(f"=> Error: {e} -> {type(e)}")


@app.get("/targets/", response_model=list[Target])
def get_targets(session: SessionDep) -> list[Target]:
    targets = session.exec(select(Target)).all()
    return targets


@app.get("/target/{target_id}", response_model=Target)
def get_target(target_id: UUID, session: SessionDep) -> Target:
    target = session.exec(select(Target).where(Target.id == target_id)).first()
    return target


@app.post("/target/", response_model=Target)
def create_target(target: TargetBase, session: SessionDep, background_tasks: BackgroundTasks) -> Target:
    existing_target = session.exec(select(Target).where(Target.ip_addr == target.ip_addr)).first()

    if existing_target:
        raise HTTPException(status_code=409, detail=f"Target with IP address {target.ip_addr} already exists.")

    db_target = Target.model_validate(target)
    session.add(db_target)
    session.commit()
    session.refresh(db_target)
    background_tasks.add_task(ping_target, target, session)
    return db_target


@app.put("/target/{target_id}", response_model=Target)
def update_target(target_id: UUID, target_data: TargetBase, session: SessionDep) -> Target:
    existing_target = session.exec(select(Target).where(Target.id == target_id)).first()
    if not existing_target:
        raise HTTPException(status_code=404, detail=f"Target with ID {target_id} not found.")
    updated_target_data = Target(id=target_id, **target_data.model_dump())
    existing_target.sqlmodel_update(updated_target_data)
    session.add(existing_target)
    session.commit()
    session.refresh(existing_target)
    return existing_target


@app.delete("/target/{target_id}")
def delete_target(target_id: UUID, session: SessionDep) -> str:
    existing_target = session.exec(select(Target).where(Target.id == target_id)).first()
    if not existing_target:
        raise HTTPException(status_code=404, detail=f"Target with ID {target_id} not found.")
    session.delete(existing_target)
    session.commit()
    return {"message": f"Target with ID {target_id} was deleted successfully!"}


@app.get("/results/", response_model=list[Result])
def get_results(session: SessionDep) -> list[Result]:
    results = session.exec(select(Result)).all()
    return results


@app.get("/monitor/{target_id}", response_model=list[Result])
def get_monitor(target_id: UUID, session: SessionDep, background_tasks: BackgroundTasks) -> list[Result]:
    target = session.exec(select(Target).where(Target.id == target_id)).first()
    background_tasks.add_task(ping_target, target, session)
    results = session.exec(select(Result).where(Result.ip_addr == target.ip_addr).order_by(Result.timestamp)).fetchall()
    return results
