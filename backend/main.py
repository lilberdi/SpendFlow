from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.core.config import settings
from backend.db.base import Base
from backend.db.schema_migrations import ensure_transaction_ocr_columns
from backend.db.session import engine

app = FastAPI(title=settings.app_name)

# React (e.g. :3000 / :5173) → FastAPI (:8000): list allowed origins in CORS_ORIGINS (see backend.core.config.Settings).
_origins = [o.strip() for o in settings.cors_origins.split(',') if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )


@app.on_event('startup')
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_transaction_ocr_columns(engine)


app.include_router(router)
