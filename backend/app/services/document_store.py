"""内存文档存储。全局单例，跨 session 共享。

本期单用户单进程、不持久化，重启丢失。
"""

import uuid
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Document:
    id: str
    filename: str
    doc_type: str  # "resume" | "qa"
    text: str
    size_bytes: int


class DocumentStore:
    """按 id 索引的文档存储（内存字典）。"""

    def __init__(self) -> None:
        self._docs: Dict[str, Document] = {}

    def add(self, filename: str, doc_type: str, text: str, size_bytes: int) -> Document:
        doc = Document(
            id=uuid.uuid4().hex,
            filename=filename,
            doc_type=doc_type,
            text=text,
            size_bytes=size_bytes,
        )
        self._docs[doc.id] = doc
        return doc

    def list(self) -> List[Document]:
        return list(self._docs.values())

    def delete(self, doc_id: str) -> bool:
        if doc_id in self._docs:
            del self._docs[doc_id]
            return True
        return False

    def get_by_type(self, doc_type: str) -> List[Document]:
        return [d for d in self._docs.values() if d.doc_type == doc_type]
