from uuid import uuid4, UUID
from datetime import datetime
from ipaddress import ip_address
from pydantic import field_validator
from sqlmodel import Field, SQLModel, String


class Result(SQLModel, table=True):
    __tablename__ = "results"
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    ip_addr: str = Field(sa_type=String(15), index=True)
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
