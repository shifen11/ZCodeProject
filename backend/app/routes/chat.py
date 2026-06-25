"""对话（SSE 流式）+ 重置 + 字幕操作 路由。

简化后的模型：
- /api/chat：发一条消息给 LLM。可选手打 message，或 send_subtitles=True 把字幕区全发。
- /api/reset：清空整个对话历史。
- /api/subtitle/*：操作字幕区（删一行/清空）。
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.deps import get_chat_service, get_session_store
from app.schemas import (
    ChatRequest,
    ClearSubtitleRequest,
    RemoveSubtitleLineRequest,
    ResetRequest,
)
from app.services.chat_service import ChatService
from app.services.session import SessionStore

router = APIRouter(prefix="/api")


@router.post("/chat")
def chat_endpoint(
    req: ChatRequest,
    store: SessionStore = Depends(get_session_store),
    svc: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """发一条消息，流式返回 LLM 回复。

    - send_subtitles=True：把字幕区全部内容打包为 user 消息，并清空字幕区。
    - 否则用 message 作为 user 消息内容。
    """
    session = store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    if req.send_subtitles:
        user_content = session.consume_subtitles()
    else:
        user_content = req.message.strip()

    if not user_content:
        raise HTTPException(status_code=400, detail="没有可发送的内容")

    def event_stream():
        try:
            for delta in svc.chat_stream(req.session_id, user_content):
                payload = json.dumps({"delta": delta}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except Exception as e:
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/reset")
def reset_endpoint(
    req: ResetRequest,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """清空整个对话历史（字幕区不动）。"""
    session = store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    session.clear_messages()
    return {"session_id": req.session_id, "reset": True}


@router.post("/subtitle/remove-line")
def remove_line_endpoint(
    req: RemoveSubtitleLineRequest,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """删除字幕区某一行。"""
    session = store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    ok = session.remove_subtitle_line(req.line_index)
    if not ok:
        raise HTTPException(status_code=400, detail="行号越界")
    return {
        "session_id": req.session_id,
        "remaining_lines": list(session.subtitle_lines),
    }


@router.post("/subtitle/clear")
def clear_subtitle_endpoint(
    req: ClearSubtitleRequest,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """清空字幕区（不影响对话历史）。"""
    session = store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    session.clear_subtitles()
    return {"session_id": req.session_id, "cleared": True}
