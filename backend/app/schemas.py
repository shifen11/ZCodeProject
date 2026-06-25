"""Pydantic 数据模型（请求/响应/内部）。"""

from pydantic import BaseModel


class Turn(BaseModel):
    """一轮问答。"""

    question: str
    suggestion: str


class SuggestRequest(BaseModel):
    session_id: str


class SuggestResponse(BaseModel):
    session_id: str
    suggestion: str
    question: str


class AskRequest(BaseModel):
    session_id: str
    message: str


class DocumentInfo(BaseModel):
    """文档元信息（列表/响应用，不含全文）。"""

    id: str
    filename: str
    doc_type: str  # "resume" | "qa"
    size_bytes: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
