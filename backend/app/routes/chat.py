"""生成建议（SSE 流式）+ 追问（SSE 流式）+ 清空历史 路由。"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.deps import get_document_store, get_llm, get_session_store, get_suggest_service
from app.prompts import build_system_prompt
from app.schemas import RemoveLineRequest, SuggestRequest
from app.services.document_store import DocumentStore
from app.services.llm import LlmClient
from app.services.session import SessionStore
from app.services.suggest import CURRENT_TURN_PREFIX, SuggestService

router = APIRouter(prefix="/api")


@router.post("/suggest")
def suggest_endpoint(
    req: SuggestRequest,
    store: SessionStore = Depends(get_session_store),
    svc: SuggestService = Depends(get_suggest_service),
) -> StreamingResponse:
    session = store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    question_override = (req.question or "").strip()
    # 预检：无手动问题且当前没有转写文本时，直接拒绝，避免空内容触发 LLM。
    if not question_override and not session.current_turn_text.strip():
        raise HTTPException(status_code=400, detail="当前没有可生成建议的内容")

    def event_stream():
        try:
            for delta in svc.suggest_stream(req.session_id, question_override):
                payload = json.dumps({"delta": delta}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except Exception as e:
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/subtitle/remove-line")
def remove_line_endpoint(
    req: RemoveLineRequest,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """删除当前轮次的某一行字幕。"""
    session = store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    ok = session.remove_line(req.line_index)
    if not ok:
        raise HTTPException(status_code=400, detail="行号越界")
    return {
        "session_id": req.session_id,
        "remaining_lines": list(session.current_turn_lines),
    }


@router.post("/subtitle/clear")
def clear_subtitle_endpoint(
    req: SuggestRequest,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """清空当前轮次的所有字幕（不影响历史轮次）。"""
    session = store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    session.clear_current_turn()
    return {"session_id": req.session_id, "cleared": True}


@router.post("/clear")
def clear_endpoint(
    req: SuggestRequest,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    session = store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    session.clear_history()
    return {"session_id": req.session_id, "cleared": True}


@router.get("/ask")
def ask_endpoint(
    session_id: str,
    message: str,
    store: SessionStore = Depends(get_session_store),
    llm: LlmClient = Depends(get_llm),
    doc_store: DocumentStore = Depends(get_document_store),
) -> StreamingResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    # 组装追问的 messages：system(含简历/题库) + 历史轮次 + 用户追问
    resume_text = "\n\n".join(d.text for d in doc_store.get_by_type("resume"))
    qa_text = "\n\n".join(d.text for d in doc_store.get_by_type("qa"))
    system_prompt = build_system_prompt(resume_text=resume_text, qa_text=qa_text)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for turn in session.history_turns:
        messages.append({"role": "user", "content": CURRENT_TURN_PREFIX + turn.question})
        messages.append({"role": "assistant", "content": turn.suggestion})
    messages.append({"role": "user", "content": message})

    async def event_stream():
        try:
            for delta in llm.stream(messages):
                payload = json.dumps({"delta": delta}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except Exception as e:
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
