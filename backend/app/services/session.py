"""会话状态管理（内存）。本期单进程、不持久化。

简化后的模型：一个会话 = 一个聊天对话历史 + 一个独立字幕暂存区。

- messages：发给 LLM 的对话历史，永远累积（整场面试一个对话）。
- subtitle_lines：语音识别出的字幕，是"采集区"，用户确认后整体发出去，
  发送时打包成一条 user message 追加进 messages，然后清空。
两者独立：删字幕/清字幕不影响对话历史。
"""

from __future__ import annotations

import uuid
from typing import Dict, List

from app.schemas import Message


class InterviewSession:
    """一场面试的一个会话。"""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        # 发给 LLM 的对话历史（role/content）。整场面试累积，不自动清。
        self.messages: List[Message] = []
        # 字幕暂存区：语音识别的定稿句子。发送给 LLM 时整体打包，然后清空。
        self.subtitle_lines: List[str] = []

    @property
    def subtitle_text(self) -> str:
        """字幕区的完整文本（换行拼接）。只读。"""
        return "\n".join(self.subtitle_lines)

    # ---- 对话历史 ----
    def add_message(self, role: str, content: str) -> None:
        """追加一条对话消息到历史。"""
        content = content.strip()
        if not content:
            return
        self.messages.append(Message(role=role, content=content))

    def clear_messages(self) -> None:
        """清空整个对话历史（重置，罕见操作）。"""
        self.messages = []

    # ---- 字幕区 ----
    def add_subtitle(self, text: str) -> None:
        """追加一句语音定稿字幕。空文本忽略。"""
        text = text.strip()
        if not text:
            return
        self.subtitle_lines.append(text)

    def remove_subtitle_line(self, index: int) -> bool:
        """删除字幕区第 index 行（0 基）。越界返回 False。"""
        if 0 <= index < len(self.subtitle_lines):
            del self.subtitle_lines[index]
            return True
        return False

    def clear_subtitles(self) -> None:
        """清空字幕区（不影响对话历史）。"""
        self.subtitle_lines = []

    def consume_subtitles(self) -> str:
        """把字幕区全部内容打包返回，并清空字幕区。空时返回空串。"""
        text = self.subtitle_text
        self.subtitle_lines = []
        return text


class SessionStore:
    """按 session_id 索引的会话存储（内存字典）。"""

    def __init__(self) -> None:
        self._sessions: Dict[str, InterviewSession] = {}

    def create(self) -> InterviewSession:
        sid = uuid.uuid4().hex
        s = InterviewSession(sid)
        self._sessions[sid] = s
        return s

    def get(self, session_id: str) -> InterviewSession | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str) -> InterviewSession:
        existing = self._sessions.get(session_id)
        if existing is not None:
            return existing
        return self.create()
