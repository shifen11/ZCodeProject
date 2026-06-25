"""测试对话 + 重置 + 字幕操作 路由。"""

import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.deps import get_chat_service, get_document_store, get_session_store
from app.main import app
from app.services.chat_service import ChatService
from app.services.document_store import DocumentStore
from app.services.session import SessionStore


def _override(store=None):
    s = store or SessionStore()
    app.dependency_overrides[get_session_store] = lambda: s
    app.dependency_overrides[get_document_store] = lambda: DocumentStore()
    return s


def _svc(store, stream_chunks):
    svc = ChatService(llm=MagicMock(), store=store)
    svc._llm.stream.return_value = iter(stream_chunks)
    app.dependency_overrides[get_chat_service] = lambda: svc
    return svc


def test_create_session_returns_id():
    store = _override()
    client = TestClient(app)
    resp = client.post("/api/session")
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    assert sid
    # session 已存在
    assert store.get(sid) is not None
    app.dependency_overrides.clear()


def test_chat_with_message_streams_reply():
    store = _override()
    s = store.create()
    _svc(store, ["回", "答"])

    client = TestClient(app)
    with client.stream(
        "POST", "/api/chat", json={"session_id": s.session_id, "message": "你好"}
    ) as resp:
        assert resp.status_code == 200
        deltas = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if "delta" in payload:
                    deltas.append(payload["delta"])
    assert "".join(deltas) == "回答"
    # 消息已追加进历史
    assert len(s.messages) == 2
    app.dependency_overrides.clear()


def test_chat_with_send_subtitles_consumes_subtitle_area():
    store = _override()
    s = store.create()
    s.add_subtitle("字幕第一句")
    s.add_subtitle("字幕第二句")
    fake = MagicMock()
    fake.stream.return_value = iter(["建议"])
    svc = ChatService(llm=fake, store=store)
    app.dependency_overrides[get_chat_service] = lambda: svc

    client = TestClient(app)
    with client.stream(
        "POST", "/api/chat", json={"session_id": s.session_id, "send_subtitles": True}
    ) as resp:
        assert resp.status_code == 200

    # 字幕区已清空，且内容作为 user 消息进了历史
    assert s.subtitle_lines == []
    assert s.messages[0].role == "user"
    assert "字幕第一句" in s.messages[0].content
    assert "字幕第二句" in s.messages[0].content
    app.dependency_overrides.clear()


def test_chat_empty_content_returns_400():
    store = _override()
    s = store.create()
    client = TestClient(app)
    resp = client.post("/api/chat", json={"session_id": s.session_id, "message": "   "})
    assert resp.status_code == 400
    app.dependency_overrides.clear()


def test_chat_unknown_session_returns_404():
    _override()
    client = TestClient(app)
    resp = client.post("/api/chat", json={"session_id": "nope", "message": "x"})
    assert resp.status_code == 404
    app.dependency_overrides.clear()


def test_reset_clears_history_only():
    store = _override()
    s = store.create()
    s.add_message("user", "hi")
    s.add_subtitle("字幕")

    client = TestClient(app)
    resp = client.post("/api/reset", json={"session_id": s.session_id})
    assert resp.status_code == 200
    assert s.messages == []
    # 字幕不动
    assert s.subtitle_lines == ["字幕"]
    app.dependency_overrides.clear()


def test_remove_subtitle_line_endpoint():
    store = _override()
    s = store.create()
    s.add_subtitle("一")
    s.add_subtitle("二")

    client = TestClient(app)
    resp = client.post(
        "/api/subtitle/remove-line",
        json={"session_id": s.session_id, "line_index": 0},
    )
    assert resp.status_code == 200
    assert resp.json()["remaining_lines"] == ["二"]
    app.dependency_overrides.clear()


def test_clear_subtitle_endpoint():
    store = _override()
    s = store.create()
    s.add_subtitle("一")
    s.add_message("user", "对话")

    client = TestClient(app)
    resp = client.post("/api/subtitle/clear", json={"session_id": s.session_id})
    assert resp.status_code == 200
    assert s.subtitle_lines == []
    assert len(s.messages) == 1
    app.dependency_overrides.clear()


def test_chat_includes_resume_in_context():
    """对话时 LLM 收到的 system 含简历。"""
    store = _override()
    s = store.create()
    docs = DocumentStore()
    docs.add(filename="r.pdf", doc_type="resume", text="简历关键词XYZ", size_bytes=10)
    app.dependency_overrides[get_document_store] = lambda: docs
    fake = MagicMock()
    fake.stream.return_value = iter(["ok"])
    svc = ChatService(llm=fake, store=store, doc_store=docs)
    app.dependency_overrides[get_chat_service] = lambda: svc

    client = TestClient(app)
    with client.stream(
        "POST", "/api/chat", json={"session_id": s.session_id, "message": "m"}
    ) as resp:
        assert resp.status_code == 200

    sent_messages = fake.stream.call_args.args[0]
    assert "简历关键词XYZ" in sent_messages[0]["content"]
    app.dependency_overrides.clear()
