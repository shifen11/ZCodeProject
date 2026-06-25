"""会话状态管理（内存）。本期单进程、不持久化。"""

from __future__ import annotations

import uuid
from typing import Dict, List

from app.schemas import Turn


class InterviewSession:
    """一场面试的一个会话。"""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        # 当前轮次累积的定稿句子（按到达顺序）。支持单句删除/全部清空。
        self.current_turn_lines: List[str] = []
        self.history_turns: List[Turn] = []

    @property
    def current_turn_text(self) -> str:
        """当前轮次的完整文本（所有定稿句子用换行拼接）。只读。"""
        return "\n".join(self.current_turn_lines)

    def append_final(self, text: str) -> None:
        """追加一句定稿字幕到当前轮次。空文本忽略。"""
        text = text.strip()
        if not text:
            return
        self.current_turn_lines.append(text)

    def remove_line(self, index: int) -> bool:
        """删除当前轮次的第 index 行（0 基）。越界返回 False。"""
        if 0 <= index < len(self.current_turn_lines):
            del self.current_turn_lines[index]
            return True
        return False

    def clear_current_turn(self) -> None:
        """清空当前轮次的所有定稿句子（不影响历史轮次）。"""
        self.current_turn_lines = []

    def finalize_turn(self, suggestion: str) -> None:
        """把当前轮次结转为历史，记录建议，清空当前轮次。"""
        self.history_turns.append(
            Turn(question=self.current_turn_text, suggestion=suggestion)
        )
        self.current_turn_lines = []

    def clear_history(self) -> None:
        """清空历史轮次，但保留当前正在进行的轮次。"""
        self.history_turns = []


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

    def clear_history(self, session_id: str) -> None:
        s = self.get(session_id)
        if s is not None:
            s.clear_history()
