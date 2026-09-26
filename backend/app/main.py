"""OwnIt API. Stateless: request text is processed in memory and never stored."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import (
    routes_analyze,
    routes_assess,
    routes_doctor,
    routes_export,
    routes_health,
    routes_humanize,
    routes_personalize,
    routes_style,
    routes_walkthrough,
)
from app.config import settings
from app.core.nlp import get_languagetool, get_lm, get_nlp
from app.deps import limiter

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_nlp()  # warm up heavy singletons once
    get_lm()
    from nltk.corpus import wordnet

    wordnet.ensure_loaded()
    get_languagetool().check("Warm up the grammar checker.")
    yield


app = FastAPI(
    title="OwnIt API",
    version="0.1.0",
    description="Humanize it. Understand it. Own it. Rule-based, no AI models, no external APIs.",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(routes_health.router)
app.include_router(routes_analyze.router)
app.include_router(routes_humanize.router)
app.include_router(routes_style.router)
app.include_router(routes_walkthrough.router)
app.include_router(routes_personalize.router)
app.include_router(routes_assess.router)
app.include_router(routes_doctor.router)
app.include_router(routes_export.router)
