"""测试生成建议 / 追问 / 清空 路由。"""

import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.deps import get_document_store, get_llm, get_session_store, get_suggest_service
from app.main import app
from app.services.document_store import DocumentStore
from app.services.session import SessionStore
from app.services.suggest import SuggestService


def _setup_session_with_turn():
    store = SessionStore()
    s = store.create()
    s.append_final("讲讲项目")
    app.dependency_overrides[get_session_store] = lambda: store
    return store, s


def test_suggest_endpoint_streams_suggestion():
    store, s = _setup_session_with_turn()
    fake_llm = MagicMock()
    fake_llm.stream.return_value = iter(["用 ", "STAR ", "回答"])
    svc = SuggestService(llm=fake_llm, store=store)
    app.dependency_overrides[get_suggest_service] = lambda: svc

    client = TestClient(app)
    with client.stream("POST", "/api/suggest", json={"session_id": s.session_id}) as resp:
        assert resp.status_code == 200
        deltas = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if "delta" in payload:
                    deltas.append(payload["delta"])
    assert "".join(deltas) == "用 STAR 回答"
    # 流式结束后：当前轮次已清空，建议已存进 history
    assert s.current_turn_text == ""
    assert s.history_turns[-1].question == "讲讲项目"
    assert s.history_turns[-1].suggestion == "用 STAR 回答"
    app.dependency_overrides.clear()


def test_suggest_unknown_session_returns_404():
    _setup_session_with_turn()
    client = TestClient(app)
    resp = client.post("/api/suggest", json={"session_id": "nonexistent"})
    assert resp.status_code == 404
    app.dependency_overrides.clear()


def test_suggest_empty_turn_returns_400():
    store, s = _setup_session_with_turn()
    s.clear_current_turn()  # 没有转写文本
    fake_llm = MagicMock()
    svc = SuggestService(llm=fake_llm, store=store)
    app.dependency_overrides[get_suggest_service] = lambda: svc

    client = TestClient(app)
    resp = client.post("/api/suggest", json={"session_id": s.session_id})
    assert resp.status_code == 400
    fake_llm.stream.assert_not_called()
    app.dependency_overrides.clear()


def test_clear_endpoint_clears_history_only():
    store, s = _setup_session_with_turn()
    s.finalize_turn(suggestion="a")
    s.append_final("当前")

    client = TestClient(app)
    resp = client.post("/api/clear", json={"session_id": s.session_id})
    assert resp.status_code == 200
    assert s.history_turns == []
    # 当前进行中的轮次不动
    assert s.current_turn_text == "当前"
    app.dependency_overrides.clear()


def test_ask_endpoint_streams_chunks():
    store, s = _setup_session_with_turn()
    s.finalize_turn(suggestion="原始建议")
    fake_llm = MagicMock()
    fake_llm.stream.return_value = iter(["你", "好"])
    app.dependency_overrides[get_llm] = lambda: fake_llm
    app.dependency_overrides[get_document_store] = lambda: DocumentStore()

    client = TestClient(app)
    with client.stream(
        "GET",
        "/api/ask",
        params={"session_id": s.session_id, "message": "再详细"},
    ) as resp:
        assert resp.status_code == 200
        deltas = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                deltas.append(json.loads(line[6:])["delta"])
    assert "".join(deltas) == "你好"
    app.dependency_overrides.clear()


def test_ask_endpoint_includes_resume_in_context():
    store, s = _setup_session_with_turn()
    s.finalize_turn(suggestion="原始建议")
    docs = DocumentStore()
    docs.add(filename="r.pdf", doc_type="resume", text="简历关键词XYZ", size_bytes=10)
    app.dependency_overrides[get_document_store] = lambda: docs
    fake_llm = MagicMock()
    fake_llm.stream.return_value = iter(["ok"])
    app.dependency_overrides[get_llm] = lambda: fake_llm

    client = TestClient(app)
    with client.stream("GET", "/api/ask", params={"session_id": s.session_id, "message": "m"}) as resp:
        assert resp.status_code == 200

    sent_messages = fake_llm.stream.call_args.args[0]
    assert "简历关键词XYZ" in sent_messages[0]["content"]
    app.dependency_overrides.clear()


def test_ask_unknown_session_returns_404():
    _setup_session_with_turn()
    client = TestClient(app)
    resp = client.get(
        "/api/ask", params={"session_id": "nonexistent", "message": "hi"}
    )
    assert resp.status_code == 404
    app.dependency_overrides.clear()
