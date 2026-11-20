"""Only the Keitaro endpoints used by the assignment."""

import json
from copy import deepcopy

import httpx


class KeitaroStub:
    def __init__(self):
        self.offers = {
            ident: {"id": ident, "name": name, "state": "active"}
            for ident, name in enumerate(["Alpha", "Beta", "Gamma", "Delta", "Epsilon"], 201)
        }
        self.campaigns = {9312: {"id": 9312, "name": "Demo"}}
        self.streams = {
            301: {
                "id": 301,
                "campaign_id": 9312,
                "name": "GEO",
                "schema": "redirect",
                "position": 1,
                "offers": [],
            },
            302: {
                "id": 302,
                "campaign_id": 9312,
                "name": "Offers",
                "schema": "landings",
                "position": 2,
                "offers": [
                    {"offer_id": 201, "share": 34, "state": "active"},
                    {"offer_id": 202, "share": 33, "state": "active"},
                    {"offer_id": 203, "share": 33, "state": "active"},
                ],
            },
        }
        self.calls = []
        self.transport = httpx.MockTransport(self.handle)

    def handle(self, request):
        assert request.url.host == "keitaro.test"
        path = request.url.path.removeprefix("/admin_api/v1")
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, path, body))
        parts = path.strip("/").split("/")
        if request.method == "GET":
            if path == "/offers":
                value = list(self.offers.values())
            elif path in {"/domains", "/groups", "/traffic_sources"}:
                value = [
                    {
                        "id": {"/domains": 101, "/groups": 102, "/traffic_sources": 103}[path],
                        "name": "FORTESTS",
                    }
                ]
            elif len(parts) == 3 and parts[0] == "campaigns":
                value = [
                    row for row in self.streams.values() if row["campaign_id"] == int(parts[1])
                ]
            else:
                value = getattr(self, parts[0]).get(int(parts[1]))
                if value is None:
                    return httpx.Response(404, json={})
        elif request.method == "POST" and path in {"/campaigns", "/streams"}:
            store = getattr(self, parts[0])
            ident = max(store, default=10000) + 1
            value = {"id": ident, "offers": [], **body}
            store[ident] = value
        elif request.method == "PUT" and parts[0] == "streams":
            value = self.streams[int(parts[1])]
            value.update(body)
        else:
            raise AssertionError((request.method, path))
        return httpx.Response(200, json=deepcopy(value))
