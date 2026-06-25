"""生成建议业务：组装 prompt，调 LLM，结转轮次。

支持两种模式：
- suggest()：同步生成，一次性返回完整建议（仍保留，测试用）。
- suggest_stream()：流式生成，逐 token 产出；流结束后才把完整建议结转进 history。
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, List

from app.prompts import build_system_prompt
from app.services.llm import LlmClient
from app.services.session import InterviewSession, SessionStore

if TYPE_CHECKING:
    from app.services.document_store import DocumentStore

CURRENT_TURN_PREFIX = "面试官问："


@dataclass
class SuggestSnapshot:
    """流式生成开始前对当前轮次的快照。"""

    question: str


class SuggestService:
    def __init__(
        self,
        llm: LlmClient,
        store: SessionStore,
        doc_store: "DocumentStore | None" = None,
    ) -> None:
        self._llm = llm
        self._store = store
        self._doc_store = doc_store

    def build_messages(self, session: InterviewSession, question_override: str = "") -> List[dict]:
        """组装 messages：system(含文档) + 历史 + 当前 user。

        question_override 非空时，用它作为当前问题（手动输入场景），
        不读 session.current_turn_text。
        """
        system_prompt = self._build_system_prompt_with_docs()
        messages: List[dict] = [{"role": "system", "content": system_prompt}]
        for turn in session.history_turns:
            messages.append({"role": "user", "content": CURRENT_TURN_PREFIX + turn.question})
            messages.append({"role": "assistant", "content": turn.suggestion})
        current_q = question_override if question_override else session.current_turn_text
        messages.append({"role": "user", "content": CURRENT_TURN_PREFIX + current_q})
        return messages

    def _build_system_prompt_with_docs(self) -> str:
        """从 doc_store 取简历/题库全文，拼进 system prompt。无 doc_store 时用基础 prompt。"""
        if self._doc_store is None:
            return build_system_prompt(resume_text="", qa_text="")
        resume_text = "\n\n".join(d.text for d in self._doc_store.get_by_type("resume"))
        qa_text = "\n\n".join(d.text for d in self._doc_store.get_by_type("qa"))
        return build_system_prompt(resume_text=resume_text, qa_text=qa_text)

    def suggest(self, session_id: str) -> str:
        """同步生成并结转当前轮次。返回建议文本。"""
        session = self._store.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        messages = self.build_messages(session)
        suggestion = self._llm.generate(messages)
        session.finalize_turn(suggestion=suggestion)
        return suggestion

    def prepare_stream(
        self, session_id: str, question_override: str = ""
    ) -> tuple[SuggestSnapshot, List[dict]]:
        """流式生成的准备阶段。

        1. 组装 messages（含当前轮次文本，或 question_override 手动问题）。
        2. 拍下 question 快照（供前端回显）。
        3. 非手动模式：立即清空当前轮次，识别可马上累积下一轮。
           手动模式：不动 session.current_turn_text（手动问题与语音累积互不影响）。

        返回 (快照, messages)。流结束后再调 commit_stream 把建议存进 history。
        """
        session = self._store.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        if question_override:
            snapshot = SuggestSnapshot(question=question_override)
            messages = self.build_messages(session, question_override=question_override)
        else:
            snapshot = SuggestSnapshot(question=session.current_turn_text)
            messages = self.build_messages(session)
            # 语音模式才清空当前轮次（手动问题不碰语音累积）
            session.clear_current_turn()
        return snapshot, messages

    def commit_stream(self, session_id: str, snapshot: SuggestSnapshot, suggestion: str) -> None:
        """流式结束后：把这一轮的 {问题, 建议} 存进 history。"""
        from app.schemas import Turn

        session = self._store.get(session_id)
        if session is None:
            return
        session.history_turns.append(
            Turn(question=snapshot.question, suggestion=suggestion)
        )

    def suggest_stream(self, session_id: str, question_override: str = "") -> Iterator[str]:
        """流式生成并结转当前轮次。逐 token 产出建议片段。

        question_override 非空时走手动输入模式（不读/不清 session 累积）。
        """
        snapshot, messages = self.prepare_stream(session_id, question_override)
        acc: list[str] = []
        for delta in self._llm.stream(messages):
            acc.append(delta)
            yield delta
        self.commit_stream(session_id, snapshot, "".join(acc))
