from datetime import datetime
from sqlmodel import Session, select
from typing import Optional
from uuid import UUID

from .models import Result, Target, TargetBase  # Import models


class PingerRepository:
    """A Repository for managing Target and Result data."""

    def __init__(self, session: Session):
        self.session = session

    # --- Target CRUD ---

    def get_all_targets(self) -> list[Target]:
        return self.session.exec(select(Target)).all()

    def get_target_by_id(self, target_id: UUID) -> Optional[Target]:
        return self.session.exec(select(Target).where(Target.id == target_id)).first()

    def get_target_by_ip(self, ip_addr: str) -> Optional[Target]:
        return self.session.exec(select(Target).where(Target.ip_addr == ip_addr)).first()

    def create_target(self, target_data: TargetBase) -> Target:
        db_target = Target.model_validate(target_data)
        self.session.add(db_target)
        self.session.commit()
        self.session.refresh(db_target)
        return db_target

    def update_target(self, target_id: UUID, target_data: TargetBase) -> Optional[Target]:
        existing_target = self.get_target_by_id(target_id)
        if existing_target:
            updated_target_data = Target(id=target_id, **target_data.model_dump())
            existing_target.sqlmodel_update(updated_target_data)
            self.session.add(existing_target)
            self.session.commit()
            self.session.refresh(existing_target)
            return existing_target
        return None

    def delete_target(self, target_id: UUID) -> bool:
        existing_target = self.get_target_by_id(target_id)
        if existing_target:
            self.session.delete(existing_target)
            self.session.commit()
            return True
        return False

    # --- Result CRUD ---

    def create_result(self, result: Result):
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)

    def get_all_results(self) -> list[Result]:
        return self.session.exec(select(Result)).all()

    def get_results_by_ip(self, ip_addr: str) -> list[Result]:
        return self.session.exec(select(Result).where(Result.ip_addr == ip_addr).order_by(Result.timestamp)).fetchall()

    def get_latest_result_timestamp(self, ip_addr: str) -> Optional[datetime]:
        statement = select(Result.timestamp).where(Result.ip_addr == ip_addr).order_by(Result.timestamp.desc())
        return self.session.exec(statement).first()
