from datetime import datetime
from uuid import uuid4, UUID
from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Field, Session, SQLModel, String, create_engine, select
from pydantic import field_validator
from ipaddress import IPv4Address, ip_address
from typing import Annotated


class Result(SQLModel, table=True):
    __tablename__ = "results"
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    ip_addr: str = Field(sa_type=String(15), index=True, unique=True)
    timestamp: datetime
    sent: int
    rcvd: int
    loss: float
    rtt_min: float
    rtt_avg: float
    rtt_max: float

    @field_validator("ip_addr", mode="before")
    @classmethod
    def validate_ip(cls, v):
        if isinstance(v, str):
            ip_address(v)
            return v
        return str(v)


class TargetBase(SQLModel):
    ip_addr: str = Field(sa_type=String(15))
    count: int
    timeout: int
    size: int
    wait: float
    interval: int

    @field_validator("ip_addr", mode="before")
    @classmethod
    def validate_ip(cls, v):
        if isinstance(v, str):
            ip_address(v)
            return v
        return str(v)


class Target(TargetBase, table=True):
    __tablename__ = "targets"
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)


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


@app.post("/target", response_model=Target)
def add_target(target: TargetBase, session: SessionDep) -> Target:
    existing_target = session.exec(select(Target).where(Target.ip_addr == target.ip_addr)).first()

    if existing_target:
        raise HTTPException(status_code=409, detail=f"Target with IP address {target.ip_addr} already exists.")

    db_target = Target.model_validate(target)
    session.add(db_target)
    session.commit()
    session.refresh(db_target)
    return db_target


@app.get("/targets", response_model=list[Target])
def get_targets(session: SessionDep) -> list[Target]:
    targets = session.exec(select(Target)).all()
    return targets


@app.get("/results", response_model=list[Result])
def get_results(session: SessionDep) -> list[Result]:
    results = session.exec(select(Result)).all()
    return results
