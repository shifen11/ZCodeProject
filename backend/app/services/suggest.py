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

    def build_messages(self, session: InterviewSession) -> List[dict]:
        """组装 messages：system(含文档) + 历史 + 当前 user。"""
        system_prompt = self._build_system_prompt_with_docs()
        messages: List[dict] = [{"role": "system", "content": system_prompt}]
        for turn in session.history_turns:
            messages.append({"role": "user", "content": CURRENT_TURN_PREFIX + turn.question})
            messages.append({"role": "assistant", "content": turn.suggestion})
        messages.append(
            {"role": "user", "content": CURRENT_TURN_PREFIX + session.current_turn_text}
        )
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

    def prepare_stream(self, session_id: str) -> tuple[SuggestSnapshot, List[dict]]:
        """流式生成的准备阶段。

        1. 组装 messages（含当前轮次文本）。
        2. 拍下 question 快照（= 当前轮次文本，供前端回显）。
        3. 立即清空当前轮次：识别可以马上开始累积下一轮，不与生成冲突。

        返回 (快照, messages)。流结束后再调 commit_stream 把建议存进 history。
        """
        session = self._store.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        snapshot = SuggestSnapshot(question=session.current_turn_text)
        messages = self.build_messages(session)
        # 立即清空当前轮次，开始新一轮累积（消息已经组装好，不受影响）
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

    def suggest_stream(self, session_id: str) -> Iterator[str]:
        """流式生成并结转当前轮次。逐 token 产出建议片段。"""
        snapshot, messages = self.prepare_stream(session_id)
        acc: list[str] = []
        for delta in self._llm.stream(messages):
            acc.append(delta)
            yield delta
        self.commit_stream(session_id, snapshot, "".join(acc))
