"""测试生成建议业务逻辑。"""

from unittest.mock import MagicMock

import pytest

from app.prompts import SYSTEM_PROMPT
from app.services.session import SessionStore
from app.services.suggest import CURRENT_TURN_PREFIX, SuggestService


def _fake_llm(return_text: str) -> MagicMock:
    llm = MagicMock()
    llm.generate.return_value = return_text
    return llm


def test_build_messages_for_first_turn():
    store = SessionStore()
    s = store.create()
    s.append_final("讲讲你最有挑战的项目")
    svc = SuggestService(llm=_fake_llm("建议"), store=store)

    msgs = svc.build_messages(s)

    assert msgs[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert msgs[-1] == {"role": "user", "content": "面试官问：讲讲你最有挑战的项目"}


def test_build_messages_includes_history_after_finalized():
    store = SessionStore()
    s = store.create()
    s.append_final("第一个问题")
    s.finalize_turn(suggestion="第一个建议")
    s.append_final("第二个问题")
    svc = SuggestService(llm=_fake_llm("x"), store=store)

    msgs = svc.build_messages(s)

    # system + 1条历史user + 1条历史assistant + 当前user
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": CURRENT_TURN_PREFIX + "第一个问题"}
    assert msgs[2] == {"role": "assistant", "content": "第一个建议"}
    assert msgs[3]["role"] == "user"


def test_suggest_calls_llm_and_finalizes_turn():
    store = SessionStore()
    s = store.create()
    s.append_final("问题X")
    llm = _fake_llm("建议Y")
    svc = SuggestService(llm=llm, store=store)

    result = svc.suggest(s.session_id)

    assert result == "建议Y"
    # 轮次已结转
    assert s.current_turn_text == ""
    assert s.history_turns[-1].suggestion == "建议Y"
    assert s.history_turns[-1].question == "问题X"


def test_suggest_unknown_session_raises():
    store = SessionStore()
    svc = SuggestService(llm=_fake_llm("x"), store=store)
    with pytest.raises(KeyError):
        svc.suggest("nonexistent-session-id")


def test_suggest_stream_emits_chunks_and_commits_turn():
    store = SessionStore()
    s = store.create()
    s.append_final("讲讲项目")
    fake_llm = MagicMock()
    fake_llm.stream.return_value = iter(["用 ", "STAR"])
    svc = SuggestService(llm=fake_llm, store=store)

    chunks = list(svc.suggest_stream(s.session_id))

    assert "".join(chunks) == "用 STAR"
    # 当前轮次在 prepare 阶段就清空了
    assert s.current_turn_text == ""
    # 流结束后建议存进 history
    assert s.history_turns[-1].question == "讲讲项目"
    assert s.history_turns[-1].suggestion == "用 STAR"


def test_suggest_stream_unknown_session_raises():
    store = SessionStore()
    svc = SuggestService(llm=MagicMock(), store=store)
    with pytest.raises(KeyError):
        list(svc.suggest_stream("nonexistent"))
