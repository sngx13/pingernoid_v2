from sqlmodel import Session, create_engine, SQLModel
from typing import Annotated
from fastapi import Depends


sqlite_file_name = "pingernoid.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    """Creates the database and all tables defined in SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency that yields a database session."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
