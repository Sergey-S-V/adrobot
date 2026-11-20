"""The creator from the task text and the editor demonstrated in the video."""


def fetch(client):
    response = client.post("/api/v1/campaigns/fetch/9312")
    assert response.status_code == 200, response.text
    campaign = response.json()
    return campaign, next(row for row in campaign["streams"] if row["editable"])


def edit(client, stream, action, offer_id=None):
    path = f"/api/v1/streams/{stream['id']}"
    if action == "add":
        response = client.post(path + "/offers", json={"keitaro_offer_id": offer_id})
    elif action in {"cancel", "publish"}:
        response = client.post(path + "/" + action)
    else:
        link = next(row for row in stream["offers"] if row["keitaro_offer_id"] == offer_id)
        path += f"/offers/{link['id']}/{action}"
        response = client.put(path, json={"pinned": True}) if action == "pin" else client.post(path)
    assert response.status_code == 200, response.text
    return response.json()


def shares(stream):
    return {
        row["keitaro_offer_id"]: row["share"]
        for row in stream["offers"]
        if row["state"] == "active"
    }


def test_campaign_creator(client):
    client.remote.offers[299] = {"id": 299, "name": "Fresh offer"}
    assert client.get("/api/v1/offers/search?query=Fresh").json() == [
        {"id": 299, "name": "Fresh offer"}
    ]
    assert client.get("/api/v1/offers/search?query=299").json() == [
        {"id": 299, "name": "Fresh offer"}
    ]
    response = client.post(
        "/api/v1/campaigns",
        json={
            "name": "AU Test",
            "geo_codes": ["AU"],
            "keitaro_offer_id": 299,
            "domain_keitaro_id": 101,
            "group_keitaro_id": 102,
            "source_keitaro_id": 103,
        },
    )
    assert response.status_code == 200, response.text
    campaign = response.json()
    external = client.remote.campaigns[campaign["keitaro_id"]]
    assert external["name"] == "AU Test" and external["type"] == "position"
    assert (external["domain_id"], external["group_id"], external["traffic_source_id"]) == (
        101,
        "102",
        103,
    )
    flows = sorted(
        (row for row in client.remote.streams.values() if row["campaign_id"] == external["id"]),
        key=lambda row: row["position"],
    )
    assert len(flows) == 2
    assert flows[0]["filters"] == [{"name": "country", "mode": "accept", "payload": ["AU"]}]
    assert flows[0]["action_payload"] == "https://google.com"
    assert flows[1]["filters"] == []
    assert flows[1]["offers"] == [{"offer_id": 299, "share": 100, "state": "active"}]


def test_editor_video(client):
    campaign, stream = fetch(client)
    geo = next(row for row in campaign["streams"] if not row["editable"])
    assert geo["offers"] == [] and "filters" not in geo
    assert shares(stream) == {201: 34, 202: 33, 203: 33}

    draft = edit(client, stream, "add", 204)
    assert shares(draft) == {201: 25, 202: 25, 203: 25, 204: 25}
    assert draft["dirty"] and len(client.remote.streams[302]["offers"]) == 3
    confirmed = edit(client, draft, "publish")
    assert not confirmed["dirty"] and len(client.remote.streams[302]["offers"]) == 4

    cancelled = edit(client, edit(client, confirmed, "add", 205), "cancel")
    assert cancelled["offers"] == confirmed["offers"] and not cancelled["dirty"]
    cleaned = edit(client, edit(client, cancelled, "add", 205), "remove", 205)
    assert cleaned["offers"] == confirmed["offers"] and not cleaned["dirty"]

    removed = edit(client, cleaned, "remove", 203)
    archived = next(row for row in removed["offers"] if row["keitaro_offer_id"] == 203)
    assert (archived["state"], archived["share"]) == ("removed", 0)
    edit(client, removed, "publish")
    assert 203 not in {row["offer_id"] for row in client.remote.streams[302]["offers"]}
    assert 203 in client.remote.offers
    restored = edit(client, removed, "restore", 203)
    assert (
        next(row for row in restored["offers"] if row["keitaro_offer_id"] == 203)["id"]
        == archived["id"]
    )
    assert shares(restored) == {201: 25, 202: 25, 203: 25, 204: 25}
    edit(client, restored, "publish")

    client.remote.streams[302]["offers"] = [
        {"offer_id": 201, "share": 25, "state": "active"},
        {"offer_id": 204, "share": 75, "state": "active"},
    ]
    _, external = fetch(client)
    assert {row["keitaro_offer_id"] for row in external["offers"] if row["state"] == "removed"} == {
        202,
        203,
    }
    pinned = edit(client, external, "pin", 201)
    draft = edit(client, pinned, "restore", 202)
    assert shares(draft) == {201: 25, 202: 38, 204: 37}
    edit(client, draft, "publish")
    assert {row["offer_id"]: row["share"] for row in client.remote.streams[302]["offers"]} == {
        201: 25,
        202: 38,
        204: 37,
    }

    # Pin itself preserves current weights; Add then divides only the free remainder.
    client.remote.streams[302]["offers"] = [
        {"offer_id": 202, "share": 10, "state": "active"},
        {"offer_id": 203, "share": 20, "state": "active"},
        {"offer_id": 204, "share": 70, "state": "active"},
    ]
    _, external = fetch(client)
    pinned = edit(client, external, "pin", 202)
    assert shares(pinned) == {202: 10, 203: 20, 204: 70}
    assert shares(edit(client, pinned, "add", 205)) == {202: 10, 203: 30, 204: 30, 205: 30}

    del client.remote.streams[302]
    refreshed = client.post("/api/v1/campaigns/fetch/9312").json()
    assert [row["keitaro_id"] for row in refreshed["streams"]] == [301]
    assert client.get(f"/api/v1/campaigns/{campaign['id']}").json() == refreshed
