from datetime import datetime
from uuid import UUID
from fastapi import Depends, FastAPI
from sqlmodel import Field, Session, SQLModel, create_engine, select
from ipaddress import IPv4Address
from typing import Annotated


class Result(SQLModel, table=True):
    __tablename__ = "results"
    id: UUID | None = Field(default=None, primary_key=True)
    ip_addr: IPv4Address
    timestamp: datetime
    sent: int
    rcvd: int
    loss: float
    rtt_min: float
    rtt_avg: float
    rtt_max: float


class System(SQLModel, table=True):
    __tablename__ = "system"
    id: UUID | None = Field(default=None, primary_key=True)
    timestamp: datetime
    local_ip_addr: IPv4Address
    public_ip_addr: IPv4Address


class Target(SQLModel, table=True):
    __tablename__ = "targets"
    id: UUID | None = Field(default=None, primary_key=True)
    ip_addr: IPv4Address
    count: int
    timeout: int
    size: int
    wait: float
    interval: int


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


@app.post("/target")
def add_target(target: Target, session: SessionDep) -> Target:
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


@app.get("/targets", response_model=list[Target])
def get_targets(session: SessionDep) -> list[Target]:
    targets = session.exec(select(Target)).all()
    return targets


@app.get("/results", response_model=list[Result])
def get_results(session: SessionDep) -> list[Result]:
    results = session.exec(select(Result)).all()
    return results
