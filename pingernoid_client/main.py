from fastapi import FastAPI
from .db.database import create_db_and_tables
from .routers import targets, results, monitor


app = FastAPI(title="Pingernoid API", description="A microservice for persistent ICMP monitoring.")

app.include_router(targets.router)
app.include_router(results.router)
app.include_router(monitor.router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
