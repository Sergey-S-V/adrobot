from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from adrobot.db import Campaign, Database, Stream, StreamOffer
from adrobot.keitaro import AppError, Keitaro, Payload
from adrobot.schemas import CreateCampaign


def changed(rows: list[StreamOffer]) -> bool:
    return any(
        (row.base_state, row.base_share, row.base_pin_share)
        != (row.draft_state, row.draft_share, row.draft_pin_share)
        for row in rows
    )


def rebalance(rows: list[StreamOffer]) -> None:
    active = [row for row in rows if row.draft_state == "active"]
    pinned = [row for row in active if row.draft_pin_share is not None]
    free = sorted(
        (row for row in active if row.draft_pin_share is None), key=lambda row: row.allocation_order
    )
    for row in pinned:
        row.draft_share = row.draft_pin_share or 0
    if free:
        quotient, remainder = divmod(100 - sum(row.draft_share for row in pinned), len(free))
        for index, row in enumerate(free):
            row.draft_share = quotient + int(index < remainder)


def links(session: Session, stream: Stream) -> list[StreamOffer]:
    return list(
        session.scalars(
            select(StreamOffer)
            .where(StreamOffer.stream_id == stream.id)
            .order_by(StreamOffer.allocation_order)
        )
    )


def stream_view(session: Session, stream: Stream) -> Payload:
    rows = links(session, stream)
    return {
        "id": str(stream.id),
        "keitaro_id": stream.keitaro_id,
        "name": stream.name,
        "editable": stream.schema == "landings",
        "dirty": changed(rows),
        "offers": [
            {
                "id": str(row.id),
                "keitaro_offer_id": row.keitaro_offer_id,
                "name": row.name,
                "state": row.draft_state or "removed",
                "share": row.draft_share,
                "pinned": row.draft_pin_share is not None,
            }
            for row in rows
        ],
    }


def campaign_view(session: Session, campaign: Campaign) -> Payload:
    streams = session.scalars(
        select(Stream)
        .where(Stream.campaign_id == campaign.id)
        .order_by(Stream.position, Stream.keitaro_id)
    )
    return {
        "id": str(campaign.id),
        "keitaro_id": campaign.keitaro_id,
        "name": campaign.name,
        "streams": [stream_view(session, row) for row in streams],
    }


def fetch_campaign(database: Database, remote: Keitaro, ident: int) -> Payload:
    header = remote.request("GET", f"/campaigns/{ident}")
    streams = remote.request("GET", f"/campaigns/{ident}/streams")
    if not isinstance(header, dict) or header.get("id") != ident or not isinstance(streams, list):
        raise AppError("Некорректный ответ Keitaro.", 502)
    cards = {}
    for raw in streams:
        if (
            not isinstance(raw, dict)
            or raw.get("campaign_id") != ident
            or not isinstance(raw.get("offers", []), list)
        ):
            raise AppError("Некорректный ответ Keitaro.", 502)
        for entry in raw.get("offers", []):
            offer_id = entry["offer_id"]
            if offer_id not in cards:
                cards[offer_id] = remote.request("GET", f"/offers/{offer_id}")
    with database.sessions.begin() as session:
        campaign = session.scalar(select(Campaign).where(Campaign.keitaro_id == ident))
        if campaign is None:
            campaign = Campaign(keitaro_id=ident, name=header["name"])
            session.add(campaign)
            session.flush()
        campaign.name = header["name"]
        incoming_stream_ids = {raw["id"] for raw in streams}
        for saved_stream in session.scalars(
            select(Stream).where(
                Stream.campaign_id == campaign.id,
                Stream.keitaro_id.not_in(incoming_stream_ids),
            )
        ):
            session.execute(delete(StreamOffer).where(StreamOffer.stream_id == saved_stream.id))
            session.delete(saved_stream)
        for raw in streams:
            stream = session.scalar(select(Stream).where(Stream.keitaro_id == raw["id"]))
            if stream is None:
                stream = Stream(
                    campaign_id=campaign.id,
                    keitaro_id=raw["id"],
                    name=raw.get("name", ""),
                    schema=raw.get("schema", ""),
                )
                session.add(stream)
                session.flush()
            stream.name, stream.schema = raw.get("name", ""), raw.get("schema", "")
            stream.position = raw.get("position", 0)
            rows = links(session, stream)
            existing = {row.keitaro_offer_id: row for row in rows}
            incoming = set()
            for index, entry in enumerate(raw.get("offers", [])):
                offer_id = entry["offer_id"]
                incoming.add(offer_id)
                row = existing.get(offer_id)
                if row is None:
                    row = StreamOffer(
                        stream_id=stream.id,
                        keitaro_offer_id=offer_id,
                        name=cards[offer_id]["name"],
                        allocation_order=max((r.allocation_order for r in rows), default=0)
                        + index
                        + 1,
                    )
                    session.add(row)
                row.name = cards[offer_id].get("name", str(offer_id))
                pin = (
                    entry["share"]
                    if row.base_pin_share is not None and entry.get("state", "active") == "active"
                    else None
                )
                row.base_state = row.draft_state = entry.get("state", "active")
                row.base_share = row.draft_share = entry["share"]
                row.base_pin_share = row.draft_pin_share = pin
                row.ever_published = True
            for row in rows:
                if row.keitaro_offer_id not in incoming:
                    if not row.ever_published:
                        session.delete(row)
                    else:
                        row.base_state = row.draft_state = None
                        row.base_share = row.draft_share = 0
                        row.base_pin_share = row.draft_pin_share = None
        session.flush()
        return campaign_view(session, campaign)


def create_campaign(database: Database, remote: Keitaro, data: CreateCampaign) -> Payload:
    remote.request("GET", f"/offers/{data.keitaro_offer_id}")
    header = remote.request(
        "POST",
        "/campaigns",
        json={
            "name": data.name,
            "alias": "adrobot-" + uuid4().hex,
            "type": "position",
            "domain_id": data.domain_keitaro_id,
            "group_id": str(data.group_keitaro_id),
            "traffic_source_id": data.source_keitaro_id,
        },
    )
    ident = header["id"]
    common = {
        "campaign_id": ident,
        "type": "regular",
        "state": "active",
        "action_type": "http",
        "collect_clicks": True,
    }
    try:
        remote.request(
            "POST",
            "/streams",
            json={
                **common,
                "name": "GEO",
                "position": 1,
                "schema": "redirect",
                "action_payload": "https://google.com",
                "filters": [{"name": "country", "mode": "accept", "payload": data.geo_codes}],
            },
        )
        remote.request(
            "POST",
            "/streams",
            json={
                **common,
                "name": "Offers",
                "position": 2,
                "schema": "landings",
                "filters": [],
                "offers": [{"offer_id": data.keitaro_offer_id, "share": 100, "state": "active"}],
            },
        )
        return fetch_campaign(database, remote, ident)
    except AppError as exc:
        raise AppError(
            f"Создание остановлено. Кампания Keitaro #{ident}: {exc.message}", exc.status
        ) from exc


def edit(
    database: Database,
    remote: Keitaro,
    ident: UUID,
    action: str,
    *,
    offer_id: int | None = None,
    link_id: UUID | None = None,
    pinned: bool = False,
) -> Payload:
    card = remote.request("GET", f"/offers/{offer_id}") if action == "add" else None
    with database.sessions.begin() as session:
        stream = session.get(Stream, ident)
        if stream is None or stream.schema != "landings":
            raise AppError("Поток офферов не найден.", 404)
        rows = links(session, stream)
        if action == "cancel":
            for saved in rows:
                if not saved.ever_published and saved.base_state is None:
                    session.delete(saved)
                else:
                    saved.draft_state, saved.draft_share, saved.draft_pin_share = (
                        saved.base_state,
                        saved.base_share,
                        saved.base_pin_share,
                    )
        else:
            if action == "add":
                row = next((row for row in rows if row.keitaro_offer_id == offer_id), None)
                if row and row.draft_state is not None:
                    raise AppError("Оффер уже есть в потоке.")
                if row is None:
                    assert card is not None and offer_id is not None
                    row = StreamOffer(
                        stream_id=stream.id,
                        keitaro_offer_id=offer_id,
                        name=card.get("name", str(offer_id)),
                        base_state=None,
                        base_share=0,
                        draft_share=0,
                        ever_published=False,
                        allocation_order=max((r.allocation_order for r in rows), default=0) + 1,
                    )
                    session.add(row)
                    rows.append(row)
                row.draft_state = "active"
            else:
                row = next((row for row in rows if row.id == link_id), None)
                if row is None:
                    raise AppError("Оффер не найден в потоке.", 404)
                if action == "remove":
                    row.draft_state, row.draft_share, row.draft_pin_share = None, 0, None
                    if not row.ever_published and row.base_state is None:
                        session.delete(row)
                        rows.remove(row)
                elif action == "restore":
                    row.draft_state = "active"
                elif action == "pin":
                    row.draft_pin_share = row.draft_share if pinned else None
            if action != "pin":
                rebalance(rows)
        session.flush()
        return stream_view(session, stream)


def publish(database: Database, remote: Keitaro, ident: UUID) -> Payload:
    with database.sessions() as session:
        stream = session.get(Stream, ident)
        if stream is None or stream.schema != "landings":
            raise AppError("Поток офферов не найден.", 404)
        rows = links(session, stream)
        active = [row for row in rows if row.draft_state == "active"]
        if active and sum(row.draft_share for row in active) != 100:
            raise AppError("Сумма активных долей должна быть 100%.")
        offers = [
            {"offer_id": row.keitaro_offer_id, "share": row.draft_share, "state": row.draft_state}
            for row in rows
            if row.draft_state is not None
        ]
        remote_id = stream.keitaro_id
        snapshot = {row.id: (row.draft_state, row.draft_share, row.draft_pin_share) for row in rows}
    remote.request("PUT", f"/streams/{remote_id}", json={"offers": offers})
    with database.sessions.begin() as session:
        stream = session.get(Stream, ident)
        assert stream is not None
        for row in links(session, stream):
            if row.id in snapshot:
                row.base_state, row.base_share, row.base_pin_share = snapshot[row.id]
                row.ever_published = row.ever_published or row.base_state is not None
        session.flush()
        return stream_view(session, stream)
