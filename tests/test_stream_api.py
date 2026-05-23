from fastapi.testclient import TestClient

from backend.app import app


def test_health() -> None:
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data.get("playground") == "/playground"
    assert data.get("stream_alt") == "/agent/stream"


def test_ground_and_ui_redirect() -> None:
    c = TestClient(app, follow_redirects=False)
    for path in ("/ground", "/ui"):
        r = c.get(path)
        assert r.status_code in (301, 302, 303, 307, 308)
        assert "/playground" in (r.headers.get("location") or "")


def test_playground_served() -> None:
    c = TestClient(app)
    r = c.get("/playground")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"Weekend Agent" in r.content


def test_root_redirects_to_playground() -> None:
    c = TestClient(app, follow_redirects=False)
    r = c.get("/")
    assert r.status_code in (301, 302, 303, 307, 308)
    assert "/playground" in (r.headers.get("location") or "")


def test_stream_agent_sse_done() -> None:
    c = TestClient(app)
    for url in ("/v1/agent/stream", "/agent/stream"):
        buf = ""
        with c.stream(
            "POST",
            url,
            json={"user_input": "下午两个人随便逛逛"},
        ) as resp:
            assert resp.status_code == 200
            for chunk in resp.iter_text():
                buf += chunk
        assert "event" in buf
        assert '"event": "done"' in buf or '"event":"done"' in buf
