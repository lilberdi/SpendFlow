from fastapi import FastAPI

from backend.api.routes import router
from backend.core.config import settings
from backend.db.base import Base
from backend.db.session import engine

app = FastAPI(title=settings.app_name)


@app.on_event('startup')
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(router)
