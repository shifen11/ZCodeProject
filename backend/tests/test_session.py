"""测试会话状态管理（单对话历史模型）。"""

import pytest

from app.services.session import SessionStore


def test_new_session_has_empty_state():
    store = SessionStore()
    s = store.create()
    assert s.messages == []
    assert s.subtitle_lines == []


def test_add_message_appends_to_history():
    store = SessionStore()
    s = store.create()
    s.add_message("user", "你好")
    s.add_message("assistant", "你好，有什么可以帮你")
    assert len(s.messages) == 2
    assert s.messages[0].role == "user"
    assert s.messages[0].content == "你好"


def test_add_message_ignores_empty():
    store = SessionStore()
    s = store.create()
    s.add_message("user", "   ")
    assert s.messages == []


def test_clear_messages_empties_history_only():
    store = SessionStore()
    s = store.create()
    s.add_message("user", "hi")
    s.add_subtitle("字幕A")
    s.clear_messages()
    assert s.messages == []
    # 字幕不受影响
    assert s.subtitle_lines == ["字幕A"]


# ---- 字幕区 ----
def test_add_subtitle_appends():
    store = SessionStore()
    s = store.create()
    s.add_subtitle("第一句")
    s.add_subtitle("第二句")
    assert s.subtitle_lines == ["第一句", "第二句"]
    assert s.subtitle_text == "第一句\n第二句"


def test_add_subtitle_ignores_empty():
    store = SessionStore()
    s = store.create()
    s.add_subtitle("有效")
    s.add_subtitle("   ")
    assert s.subtitle_lines == ["有效"]


def test_remove_subtitle_line_deletes_specific():
    store = SessionStore()
    s = store.create()
    s.add_subtitle("第一句")
    s.add_subtitle("第二句")
    s.add_subtitle("第三句")
    assert s.remove_subtitle_line(1) is True
    assert s.subtitle_lines == ["第一句", "第三句"]
    assert s.remove_subtitle_line(1) is True
    assert s.subtitle_lines == ["第一句"]


def test_remove_subtitle_line_out_of_range_returns_false():
    store = SessionStore()
    s = store.create()
    s.add_subtitle("只有一句")
    assert s.remove_subtitle_line(5) is False
    assert s.remove_subtitle_line(-1) is False


def test_clear_subtitles_empties_subtitle_only():
    store = SessionStore()
    s = store.create()
    s.add_message("user", "对话历史")
    s.add_subtitle("字幕1")
    s.add_subtitle("字幕2")
    s.clear_subtitles()
    assert s.subtitle_lines == []
    # 对话历史不受影响
    assert len(s.messages) == 1


def test_consume_subtitles_returns_text_and_clears():
    store = SessionStore()
    s = store.create()
    s.add_subtitle("第一句")
    s.add_subtitle("第二句")
    text = s.consume_subtitles()
    assert text == "第一句\n第二句"
    assert s.subtitle_lines == []


def test_consume_empty_subtitles_returns_empty():
    store = SessionStore()
    s = store.create()
    assert s.consume_subtitles() == ""


def test_store_get_or_create():
    store = SessionStore()
    s = store.create()
    assert store.get_or_create(s.session_id) is s
    assert store.get_or_create("new-id") is not s
