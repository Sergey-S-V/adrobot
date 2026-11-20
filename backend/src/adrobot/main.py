from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from adrobot import service
from adrobot.db import Campaign, Database
from adrobot.keitaro import AppError, Keitaro, Payload, Settings
from adrobot.schemas import CreateCampaign, OfferID, Pin


def create_app(
    settings: Settings | None = None, *, keitaro_transport: httpx.BaseTransport | None = None
) -> FastAPI:
    settings = settings or Settings()
    database, remote = Database(settings.database_url), Keitaro(settings, keitaro_transport)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            remote.close()
            database.close()

    app = FastAPI(
        title="Adrobot", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )

    @app.exception_handler(AppError)
    async def error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    @app.get("/api/v1/campaigns/{ident}")
    def campaign(ident: UUID) -> Payload:
        with database.sessions() as session:
            row = session.get(Campaign, ident)
            if row is None:
                raise AppError("Кампания не найдена.", 404)
            return service.campaign_view(session, row)

    @app.post("/api/v1/campaigns")
    def create(body: CreateCampaign) -> Payload:
        return service.create_campaign(database, remote, body)

    @app.post("/api/v1/campaigns/fetch/{keitaro_id}")
    def fetch(keitaro_id: int) -> Payload:
        return service.fetch_campaign(database, remote, keitaro_id)

    @app.get("/api/v1/creation-options")
    def options() -> Payload:
        return {
            "domains": remote.request("GET", "/domains"),
            "groups": remote.request("GET", "/groups", params={"type": "campaigns"}),
            "sources": remote.request("GET", "/traffic_sources"),
        }

    @app.get("/api/v1/offers/search")
    def offers(query: str = "") -> list[Payload]:
        rows = remote.request("GET", "/offers")
        needle = query.strip().casefold()
        return [
            {"id": row["id"], "name": row.get("name", str(row["id"]))}
            for row in rows
            if not needle or needle in row.get("name", "").casefold() or needle == str(row["id"])
        ]

    @app.post("/api/v1/streams/{ident}/offers")
    def add(ident: UUID, body: OfferID) -> Payload:
        return service.edit(database, remote, ident, "add", offer_id=body.keitaro_offer_id)

    @app.post("/api/v1/streams/{ident}/offers/{link_id}/remove")
    def remove(ident: UUID, link_id: UUID) -> Payload:
        return service.edit(database, remote, ident, "remove", link_id=link_id)

    @app.post("/api/v1/streams/{ident}/offers/{link_id}/restore")
    def restore(ident: UUID, link_id: UUID) -> Payload:
        return service.edit(database, remote, ident, "restore", link_id=link_id)

    @app.put("/api/v1/streams/{ident}/offers/{link_id}/pin")
    def pin(ident: UUID, link_id: UUID, body: Pin) -> Payload:
        return service.edit(database, remote, ident, "pin", link_id=link_id, pinned=body.pinned)

    @app.post("/api/v1/streams/{ident}/cancel")
    def cancel(ident: UUID) -> Payload:
        return service.edit(database, remote, ident, "cancel")

    @app.post("/api/v1/streams/{ident}/publish")
    def publish(ident: UUID) -> Payload:
        return service.publish(database, remote, ident)

    return app
