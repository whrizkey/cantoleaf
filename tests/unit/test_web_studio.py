import pytest
from httpx import ASGITransport, AsyncClient

from cantoleaf.web.app import app


@pytest.mark.asyncio
async def test_web_studio_index() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "CantoLeaf" in resp.text
        assert "Gear 3: Verbatim" in resp.text


@pytest.mark.asyncio
async def test_web_studio_inspect_book() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/book/inspect?path=tests/fixtures/sample.md")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Sample"
        assert len(data["chapters"]) == 3
