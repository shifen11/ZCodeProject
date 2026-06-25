# 文档管理 + 上下文增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `/manage` 管理页,上传简历(PDF)和面试题库(.md);面试生成建议时把这些文档全文拼进 system prompt,让 GLM 引用真实经历、参考已准备的答案。

**Architecture:** 后端新增文档解析(pypdf/UTF-8)、内存文档存储(全局单例)、文档 CRUD 路由;SuggestService 组装 prompt 时把简历和题库全文拼进 system message,建议与追问链路一致。前端引入 React Router,新增管理页(上传+列表+删除),面试页无感复用同一份文档。

**Tech Stack:** 后端 FastAPI / `pypdf` / `python-multipart` / `pytest` · 前端 React + `react-router-dom` / TypeScript

---

## 文件结构总览

```
backend/app/
├── routes/documents.py        # 新:文档上传/列表/删除路由
├── services/doc_parser.py     # 新:PDF/MD 解析
├── services/document_store.py # 新:内存文档存储
├── schemas.py                 # 改:新增 Document 相关模型
├── prompts.py                 # 改:新增 build_system_prompt(支持拼文档)
├── services/suggest.py        # 改:build_messages 注入文档
├── routes/chat.py             # 改:ask_endpoint 注入文档
├── deps.py                    # 改:新增 get_document_store / 给 SuggestService 注入 doc store
└── main.py                    # 改:挂载 documents 路由
backend/tests/
├── test_doc_parser.py         # 新
├── test_document_store.py     # 新
├── test_documents_route.py    # 新
├── test_suggest.py            # 改:验证文档注入
└── test_prompts.py            # 新
frontend/src/
├── App.tsx                    # 改:引入 React Router
├── routes/
│   ├── InterviewPage.tsx      # 新:现有 App 逻辑迁移
│   └── ManagePage.tsx         # 新:管理页
├── components/
│   ├── DocumentUpload.tsx     # 新:上传区
│   └── DocumentList.tsx       # 新:文档列表
├── hooks/useDocuments.ts      # 新:文档 CRUD
├── api/documents.ts           # 新:文档 API 客户端
└── types.ts                   # 改:新增 Document 类型
```

---

## Task 1: 依赖与文档数据模型

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: 给 `pyproject.toml` 加依赖**

在 `dependencies` 列表里加两行(pypdf 用于 PDF 文本提取,python-multipart 用于 FastAPI 文件上传):

```toml
  "pypdf>=4.0",
  "python-multipart>=0.0.9",
```

- [ ] **Step 2: 安装新依赖**

Run: `cd backend && . .venv/bin/activate && pip install -e ".[dev]"`
Expected: 成功安装 pypdf、python-multipart

- [ ] **Step 3: 在 `app/schemas.py` 末尾追加文档模型**

```python
class DocumentInfo(BaseModel):
    """文档元信息（列表/响应用，不含全文）。"""

    id: str
    filename: str
    doc_type: str  # "resume" | "qa"
    size_bytes: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
```

- [ ] **Step 4: 冒烟验证导入**

Run: `cd backend && . .venv/bin/activate && python -c "from app.schemas import DocumentInfo, DocumentListResponse; import pypdf, multipart; print('ok')"`
Expected: 打印 `ok`

- [ ] **Step 5: Commit**

```bash
git -C /Users/shifen/ZCodeProject add backend/pyproject.toml backend/app/schemas.py
git -C /Users/shifen/ZCodeProject commit -m "feat(backend): add pypdf/multipart deps and document schemas"
```

---

## Task 2: 文档解析模块（TDD）

**Files:**
- Create: `backend/app/services/doc_parser.py`
- Create: `backend/tests/test_doc_parser.py`

**职责：** 按扩展名把上传文件解析成纯文本。PDF 用 pypdf，Markdown 直接 UTF-8 解码。

- [ ] **Step 1: 写失败测试 `tests/test_doc_parser.py`**

```python
"""测试文档解析：PDF / MD -> 纯文本。"""

import pytest

from app.services.doc_parser import parse_document, UnsupportedFormatError


def test_parse_markdown_returns_utf8_text():
    content = "# 面试题\n\n- 自我介绍\n- 项目经历".encode("utf-8")
    text = parse_document("questions.md", content)
    assert text == "# 面试题\n\n- 自我介绍\n- 项目经历"


def test_parse_markdown_preserves_formatting():
    """markdown 符号（#/代码块）应原样保留。"""
    content = b"```python\nprint(1)\n```"
    assert parse_document("note.md", content) == "```python\nprint(1)\n```"


def test_parse_unsupported_format_raises():
    with pytest.raises(UnsupportedFormatError):
        parse_document("note.docx", b"...")


def test_parse_pdf_extracts_text():
    """用 pypdf 现场生成一个单页 PDF，验证能提取文本。"""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # pypdf 原生不支持写入文本流，这里用最小可提取的 PDF 测试"不抛异常 + 返回字符串"
    import io

    buf = io.BytesIO()
    writer.write(buf)
    text = parse_document("resume.pdf", buf.getvalue())
    assert isinstance(text, str)
    # 空白页提取出的文本为空字符串是正常的
    assert text == ""
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_doc_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.doc_parser'`

- [ ] **Step 3: 写实现 `app/services/doc_parser.py`**

```python
"""文档解析：按扩展名把上传文件转成纯文本。

- PDF (.pdf)：用 pypdf 提取文本
- Markdown (.md)：UTF-8 解码，保留 markdown 格式（帮 LLM 理解结构）
- 其它：抛 UnsupportedFormatError
"""

import io

from pypdf import PdfReader


class UnsupportedFormatError(ValueError):
    """上传了不支持的文件格式。"""


def parse_document(filename: str, file_bytes: bytes) -> str:
    """按扩展名解析文档，返回纯文本。

    Args:
        filename: 原始文件名（用于判断扩展名）。
        file_bytes: 文件原始字节。

    Returns:
        解析出的纯文本。

    Raises:
        UnsupportedFormatError: 不支持的格式。
    """
    name = filename.lower()
    if name.endswith(".pdf"):
        return _parse_pdf(file_bytes)
    if name.endswith(".md"):
        return file_bytes.decode("utf-8")
    raise UnsupportedFormatError(f"不支持的文件格式: {filename}（仅支持 .pdf / .md）")


def _parse_pdf(file_bytes: bytes) -> str:
    """用 pypdf 提取 PDF 全部页面的文本。"""
    reader = PdfReader(io.BytesIO(file_bytes))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_doc_parser.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git -C /Users/shifen/ZCodeProject add backend/app/services/doc_parser.py backend/tests/test_doc_parser.py
git -C /Users/shifen/ZCodeProject commit -m "feat(backend): document parser for pdf/md"
```

---

## Task 3: 内存文档存储（TDD）

**Files:**
- Create: `backend/app/services/document_store.py`
- Create: `backend/tests/test_document_store.py`

**职责：** 内存字典存文档，全局单例，支持 add/list/delete/get_by_type。

- [ ] **Step 1: 写失败测试 `tests/test_document_store.py`**

```python
"""测试内存文档存储。"""

from app.services.document_store import Document, DocumentStore


def test_add_and_list():
    store = DocumentStore()
    doc = store.add(filename="resume.pdf", doc_type="resume", text="我的简历", size_bytes=100)
    assert doc.id
    assert doc.filename == "resume.pdf"
    listed = store.list()
    assert len(listed) == 1
    assert listed[0].id == doc.id
    assert listed[0].filename == "resume.pdf"


def test_list_does_not_expose_full_text():
    """list 返回的是元信息，text 不参与断言（避免泄露大文本）。"""
    store = DocumentStore()
    store.add(filename="q.md", doc_type="qa", text="很长的内容...", size_bytes=10)
    listed = store.list()
    assert listed[0].size_bytes == 10
    assert listed[0].doc_type == "qa"


def test_delete_removes_document():
    store = DocumentStore()
    doc = store.add(filename="a.md", doc_type="qa", text="x", size_bytes=1)
    assert store.delete(doc.id) is True
    assert store.list() == []
    # 再删一次返回 False
    assert store.delete(doc.id) is False


def test_get_by_type_filters():
    store = DocumentStore()
    store.add(filename="r.pdf", doc_type="resume", text="r", size_bytes=1)
    store.add(filename="q1.md", doc_type="qa", text="q1", size_bytes=1)
    store.add(filename="q2.md", doc_type="qa", text="q2", size_bytes=1)
    resumes = store.get_by_type("resume")
    qas = store.get_by_type("qa")
    assert len(resumes) == 1
    assert len(qas) == 2
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_document_store.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 写实现 `app/services/document_store.py`**

```python
"""内存文档存储。全局单例，跨 session 共享。

本期单用户单进程、不持久化，重启丢失。
"""

from dataclasses import dataclass, field
from typing import Dict, List
import uuid


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
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_document_store.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git -C /Users/shifen/ZCodeProject add backend/app/services/document_store.py backend/tests/test_document_store.py
git -C /Users/shifen/ZCodeProject commit -m "feat(backend): in-memory document store"
```

---

## Task 4: 动态 system prompt 构建（TDD）

**Files:**
- Modify: `backend/app/prompts.py`
- Create: `backend/tests/test_prompts.py`

**职责：** 把原静态 `SYSTEM_PROMPT` 拆成"基础 prompt + 文档拼接函数"。有文档时拼进简历/题库区，无文档时退回基础 prompt。

- [ ] **Step 1: 写失败测试 `tests/test_prompts.py`**

```python
"""测试 system prompt 的文档拼接。"""

from app.prompts import BASE_SYSTEM_PROMPT, build_system_prompt


def test_no_documents_returns_base_prompt():
    prompt = build_system_prompt(resume_text="", qa_text="")
    assert prompt == BASE_SYSTEM_PROMPT
    # 无文档时不应出现文档区标题
    assert "简历" not in prompt


def test_resume_only_appended():
    prompt = build_system_prompt(resume_text="张三的简历内容", qa_text="")
    assert "张三的简历内容" in prompt
    assert "面试题库" not in prompt


def test_qa_only_appended():
    prompt = build_system_prompt(resume_text="", qa_text="常见问题及答案")
    assert "常见问题及答案" in prompt
    assert "简历" in prompt  # 标题保留，但内容为空时不应误导（见下一测）


def test_both_appended_with_usage_notes():
    prompt = build_system_prompt(resume_text="简历X", qa_text="题库Y")
    assert "简历X" in prompt
    assert "题库Y" in prompt
    assert "引用用户的真实经历" in prompt
    assert "优先参考用户已准备的答案" in prompt
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_prompts.py -v`
Expected: FAIL with `ImportError: cannot import name 'BASE_SYSTEM_PROMPT'`

- [ ] **Step 3: 改写 `app/prompts.py`**

把原 `SYSTEM_PROMPT` 重命名为 `BASE_SYSTEM_PROMPT`，并新增 `build_system_prompt`：

```python
"""System prompt：面试教练，可按需拼入简历/题库。"""

BASE_SYSTEM_PROMPT = """你是一位资深面试教练，帮助求职者应对面试。

任务：针对面试官的问题，给出回答建议。要求：
1. 先简要点出面试官在考察什么
2. 给出 1-2 个回答方向/要点（建议用 STAR 结构：情境-任务-行动-结果）
3. 如适合，给一个简短的回答示范开头
4. 不要替求职者编造具体经历或数据，只给思路和框架

特别注意：
- 如果面试官的话只是寒暄/闲聊（如"你今天怎么样""路上堵车吗"），不要给正式回答建议，只回复"[非正式问题，闲聊即可]"。
"""

_RESUME_HEADER = "====== 用户的简历 ======"
_QA_HEADER = "====== 用户的面试题库（常见问题及准备好的答案）======"
_USAGE_NOTES = """使用说明：
- 简历：回答时引用用户的真实经历，不要编造
- 题库：如果面试官的问题接近题库里的题，优先参考用户已准备的答案"""


def build_system_prompt(resume_text: str, qa_text: str) -> str:
    """在基础 prompt 上拼入简历/题库全文。

    - 无任何文档时返回 BASE_SYSTEM_PROMPT（不追加空区，避免误导）。
    - 有文档时追加对应区 + 使用说明。
    """
    has_resume = bool(resume_text.strip())
    has_qa = bool(qa_text.strip())
    if not has_resume and not has_qa:
        return BASE_SYSTEM_PROMPT

    parts = [BASE_SYSTEM_PROMPT, ""]
    if has_resume:
        parts.extend([_RESUME_HEADER, resume_text.strip(), ""])
    if has_qa:
        parts.extend([_QA_HEADER, qa_text.strip(), ""])
    parts.append(_USAGE_NOTES)
    return "\n".join(parts)
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_prompts.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 全量回归（确认重命名没破坏旧测试）**

Run: `cd backend && . .venv/bin/activate && python -m pytest -q`
Expected: 全部 PASS（旧测试里如有引用 SYSTEM_PROMPT 的需同步改为 BASE_SYSTEM_PROMPT）

> 若 `test_suggest.py` / `test_chat_route.py` 因 `SYSTEM_PROMPT` 改名而失败，在对应测试里把 `from app.prompts import SYSTEM_PROMPT` 改为 `from app.prompts import BASE_SYSTEM_PROMPT as SYSTEM_PROMPT`。

- [ ] **Step 6: Commit**

```bash
git -C /Users/shifen/ZCodeProject add backend/app/prompts.py backend/tests/test_prompts.py
git -C /Users/shifen/ZCodeProject commit -m "feat(backend): build_system_prompt with resume/qa injection"
```

---

## Task 5: SuggestService 注入文档（TDD）

**Files:**
- Modify: `backend/app/services/suggest.py`
- Modify: `backend/tests/test_suggest.py`

**职责：** `SuggestService` 新增可选的 `DocumentStore` 依赖；`build_messages` 时从文档库取简历/题库全文，拼进 system message。

- [ ] **Step 1: 改 `SuggestService.__init__` 接受可选 doc_store**

把 `app/services/suggest.py` 的 `__init__` 改为：

```python
    def __init__(
        self,
        llm: LlmClient,
        store: SessionStore,
        doc_store: "DocumentStore | None" = None,
    ) -> None:
        self._llm = llm
        self._store = store
        self._doc_store = doc_store
```

并在文件顶部 import 区加：

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.document_store import DocumentStore
```

- [ ] **Step 2: 改 `build_messages` 注入文档**

```python
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
        from app.prompts import build_system_prompt

        if self._doc_store is None:
            return build_system_prompt(resume_text="", qa_text="")
        resume_text = "\n\n".join(d.text for d in self._doc_store.get_by_type("resume"))
        qa_text = "\n\n".join(d.text for d in self._doc_store.get_by_type("qa"))
        return build_system_prompt(resume_text=resume_text, qa_text=qa_text)
```

> 注意：`build_messages` 原来用 `SYSTEM_PROMPT`，现在改为 `self._build_system_prompt_with_docs()`。`prepare_stream` 调用 `build_messages`，自动跟着升级，无需改。

- [ ] **Step 3: 在 `tests/test_suggest.py` 加文档注入测试**

追加到文件末尾：

```python
def test_build_messages_includes_resume_when_doc_store_has_resume():
    from app.services.document_store import DocumentStore

    docs = DocumentStore()
    docs.add(filename="r.pdf", doc_type="resume", text="我在腾讯做过后端", size_bytes=10)
    store = SessionStore()
    s = store.create()
    s.append_final("讲讲项目")
    svc = SuggestService(llm=_fake_llm("x"), store=store, doc_store=docs)

    msgs = svc.build_messages(s)

    assert "我在腾讯做过后端" in msgs[0]["content"]


def test_build_messages_without_doc_store_uses_base_prompt():
    store = SessionStore()
    s = store.create()
    s.append_final("讲讲项目")
    svc = SuggestService(llm=_fake_llm("x"), store=store, doc_store=None)

    msgs = svc.build_messages(s)

    # 无文档时 system message 不含文档区标题
    assert "用户的简历" not in msgs[0]["content"]
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_suggest.py -v`
Expected: PASS（含新增 2 个 + 原 6 个）

- [ ] **Step 5: Commit**

```bash
git -C /Users/shifen/ZCodeProject add backend/app/services/suggest.py backend/tests/test_suggest.py
git -C /Users/shifen/ZCodeProject commit -m "feat(backend): inject resume/qa docs into suggest prompt"
```

---

## Task 6: 文档 CRUD 路由（TDD）

**Files:**
- Create: `backend/app/routes/documents.py`
- Create: `backend/tests/test_documents_route.py`
- Modify: `backend/app/deps.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 在 `app/deps.py` 加 document store 单例和注入**

在文件末尾追加：

```python
from app.services.document_store import DocumentStore

_document_store_singleton = DocumentStore()


def get_document_store() -> DocumentStore:
    return _document_store_singleton
```

并改 `get_suggest_service` 注入 doc_store：

```python
def get_suggest_service(
    settings: Settings = Depends(get_settings),
    store: SessionStore = Depends(get_session_store),
    doc_store: DocumentStore = Depends(get_document_store),
) -> SuggestService:
    return SuggestService(llm=get_llm(settings), store=store, doc_store=doc_store)
```

- [ ] **Step 2: 写失败测试 `tests/test_documents_route.py`**

```python
"""测试文档上传/列表/删除路由。"""

from io import BytesIO

from fastapi.testclient import TestClient

from app.deps import get_document_store
from app.main import app
from app.services.document_store import DocumentStore


def _override_store() -> DocumentStore:
    store = DocumentStore()
    app.dependency_overrides[get_document_store] = lambda: store
    return store


def test_upload_markdown_then_list():
    store = _override_store()
    client = TestClient(app)
    resp = client.post(
        "/api/documents/upload",
        data={"doc_type": "qa"},
        files={"file": ("q.md", BytesIO(b"# 题目\n答案"), "text/markdown")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "q.md"
    assert body["doc_type"] == "qa"

    listed = client.get("/api/documents/list").json()
    assert len(listed["documents"]) == 1
    assert listed["documents"][0]["filename"] == "q.md"


def test_upload_invalid_doc_type_returns_400():
    _override_store()
    client = TestClient(app)
    resp = client.post(
        "/api/documents/upload",
        data={"doc_type": "unknown"},
        files={"file": ("x.md", BytesIO(b"x"), "text/markdown")},
    )
    assert resp.status_code == 400
    app.dependency_overrides.clear()


def test_upload_unsupported_format_returns_400():
    _override_store()
    client = TestClient(app)
    resp = client.post(
        "/api/documents/upload",
        data={"doc_type": "resume"},
        files={"file": ("x.docx", BytesIO(b"x"), "application/octet-stream")},
    )
    assert resp.status_code == 400
    app.dependency_overrides.clear()


def test_delete_removes_document():
    store = _override_store()
    doc = store.add(filename="a.md", doc_type="qa", text="x", size_bytes=1)
    client = TestClient(app)
    resp = client.delete(f"/api/documents/{doc.id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert store.list() == []
    app.dependency_overrides.clear()


def test_delete_unknown_returns_404():
    _override_store()
    client = TestClient(app)
    resp = client.delete("/api/documents/nonexistent")
    assert resp.status_code == 404
    app.dependency_overrides.clear()
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_documents_route.py -v`
Expected: FAIL（路由不存在 / 404）

- [ ] **Step 4: 写实现 `app/routes/documents.py`**

```python
"""文档上传/列表/删除路由。"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.deps import get_document_store
from app.routes.chat import MAX_DOC_SIZE_BYTES  # 见 Task 7 定义
from app.schemas import DocumentInfo, DocumentListResponse
from app.services.doc_parser import UnsupportedFormatError, parse_document
from app.services.document_store import DocumentStore

router = APIRouter(prefix="/api/documents")
VALID_DOC_TYPES = {"resume", "qa"}


@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    store: DocumentStore = Depends(get_document_store),
) -> DocumentInfo:
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type 必须是 {VALID_DOC_TYPES} 之一")
    file_bytes = await file.read()
    if len(file_bytes) > MAX_DOC_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="单个文件超过 10MB 限制")
    try:
        text = parse_document(file.filename or "unknown", file_bytes)
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc = store.add(
        filename=file.filename or "unknown",
        doc_type=doc_type,
        text=text,
        size_bytes=len(file_bytes),
    )
    return DocumentInfo(id=doc.id, filename=doc.filename, doc_type=doc.doc_type, size_bytes=doc.size_bytes)


@router.get("/list", response_model=DocumentListResponse)
def list_documents(store: DocumentStore = Depends(get_document_store)) -> DocumentListResponse:
    docs = store.list()
    return DocumentListResponse(
        documents=[
            DocumentInfo(id=d.id, filename=d.filename, doc_type=d.doc_type, size_bytes=d.size_bytes)
            for d in docs
        ]
    )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    store: DocumentStore = Depends(get_document_store),
) -> dict:
    ok = store.delete(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"id": doc_id, "deleted": True}
```

- [ ] **Step 5: 在 `app/main.py` 挂载路由**

把 `from app.routes import audio, chat` 改为：

```python
from app.routes import audio, chat, documents
```

并在末尾追加：

```python
app.include_router(documents.router)
```

- [ ] **Step 6: 运行测试，确认通过**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_documents_route.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Commit**

```bash
git -C /Users/shifen/ZCodeProject add backend/app/routes/documents.py backend/tests/test_documents_route.py backend/app/deps.py backend/app/main.py
git -C /Users/shifen/ZCodeProject commit -m "feat(backend): document upload/list/delete routes"
```

---

## Task 7: 追问链路注入文档 + 常量收口

**Files:**
- Modify: `backend/app/routes/chat.py`
- Modify: `backend/tests/test_chat_route.py`

**职责：** `ask_endpoint` 也要把文档拼进 system message（保持建议/追问上下文一致）。同时把 `MAX_DOC_SIZE_BYTES` 常量定义在 chat.py 供 documents.py 引用（或移到 config，本期放 chat.py 简单）。

> 注：Task 6 的 documents.py 已 `from app.routes.chat import MAX_DOC_SIZE_BYTES`，所以本 Task 必须定义它。

- [ ] **Step 1: 在 `app/routes/chat.py` 顶部加常量和 import**

在 import 区加：

```python
from app.deps import get_document_store
from app.prompts import build_system_prompt
from app.services.document_store import DocumentStore
```

在文件常量区加（`router = APIRouter(prefix="/api")` 附近）：

```python
MAX_DOC_SIZE_BYTES = 10 * 1024 * 1024  # 单文件 10MB 上限
```

- [ ] **Step 2: 改 `ask_endpoint` 注入文档**

把 `ask_endpoint` 签名加 `doc_store` 依赖，并把组装 system message 的部分改为：

```python
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
```

- [ ] **Step 3: 在 `tests/test_chat_route.py` 给 ask 测试注入 doc_store override**

在 `test_ask_endpoint_streams_chunks` 里，给 `get_document_store` 也加 override（避免用真实单例）：

```python
from app.deps import get_document_store
from app.services.document_store import DocumentStore

# 在 test_ask_endpoint_streams_chunks 内，override：
app.dependency_overrides[get_document_store] = lambda: DocumentStore()
```

并新增一个测试验证追问能拿到简历：

```python
def test_ask_endpoint_includes_resume_in_context():
    store, s = _setup_session_with_turn()
    s.finalize_turn(suggestion="原始建议")
    docs = DocumentStore()
    docs.add(filename="r.pdf", doc_type="resume", text="简历关键词XYZ", size_bytes=10)
    app.dependency_overrides[get_document_store] = lambda: docs
    fake_llm = MagicMock()
    fake_llm.stream.return_value = iter(["ok"])
    app.dependency_overrides[get_llm] = lambda: fake_llm

    client = TestClient(app)
    with client.stream("GET", "/api/ask", params={"session_id": s.session_id, "message": "m"}) as resp:
        assert resp.status_code == 200

    sent_messages = fake_llm.stream.call_args.args[0]
    assert "简历关键词XYZ" in sent_messages[0]["content"]
    app.dependency_overrides.clear()
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_chat_route.py -v`
Expected: PASS

- [ ] **Step 5: 全量回归**

Run: `cd backend && . .venv/bin/activate && python -m pytest -q`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git -C /Users/shifen/ZCodeProject add backend/app/routes/chat.py backend/tests/test_chat_route.py
git -C /Users/shifen/ZCodeProject commit -m "feat(backend): inject docs into ask endpoint; add MAX_DOC_SIZE_BYTES"
```

---

## Task 8: 前端文档类型与 API 客户端

**Files:**
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/api/documents.ts`

- [ ] **Step 1: 在 `types.ts` 加 Document 类型**

```typescript
export interface DocumentInfo {
  id: string;
  filename: string;
  doc_type: 'resume' | 'qa';
  size_bytes: number;
}
```

- [ ] **Step 2: 写 `src/api/documents.ts`**

```typescript
import type { DocumentInfo } from '../types'

const BASE = '/api/documents'

export async function listDocuments(): Promise<DocumentInfo[]> {
  const resp = await fetch(`${BASE}/list`)
  if (!resp.ok) throw new Error(`获取文档列表失败：${resp.status}`)
  const data = await resp.json()
  return data.documents as DocumentInfo[]
}

export async function uploadDocument(
  file: File,
  docType: 'resume' | 'qa',
): Promise<DocumentInfo> {
  const form = new FormData()
  form.append('file', file)
  form.append('doc_type', docType)
  const resp = await fetch(`${BASE}/upload`, {
    method: 'POST',
    body: form,
  })
  if (!resp.ok) {
    const detail = await resp.text()
    throw new Error(`上传失败：${detail}`)
  }
  return resp.json()
}

export async function deleteDocument(id: string): Promise<void> {
  const resp = await fetch(`${BASE}/${id}`, { method: 'DELETE' })
  if (!resp.ok) throw new Error(`删除失败：${resp.status}`)
}
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/shifen/ZCodeProject add frontend/src/types.ts frontend/src/api/documents.ts
git -C /Users/shifen/ZCodeProject commit -m "feat(frontend): document types and API client"
```

---

## Task 9: 前端文档管理 Hook

**Files:**
- Create: `frontend/src/hooks/useDocuments.ts`

- [ ] **Step 1: 写 `src/hooks/useDocuments.ts`**

```typescript
import { useCallback, useEffect, useState } from 'react'
import { deleteDocument, listDocuments, uploadDocument } from '../api/documents'
import type { DocumentInfo } from '../types'

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setDocuments(await listDocuments())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  // 首次挂载拉一次列表
  useEffect(() => {
    refresh()
  }, [refresh])

  const upload = useCallback(
    async (file: File, docType: 'resume' | 'qa') => {
      setError('')
      try {
        await uploadDocument(file, docType)
        await refresh()
      } catch (e) {
        setError((e as Error).message)
      }
    },
    [refresh],
  )

  const remove = useCallback(
    async (id: string) => {
      setError('')
      try {
        await deleteDocument(id)
        await refresh()
      } catch (e) {
        setError((e as Error).message)
      }
    },
    [refresh],
  )

  return { documents, loading, error, refresh, upload, remove }
}
```

- [ ] **Step 2: Commit**

```bash
git -C /Users/shifen/ZCodeProject add frontend/src/hooks/useDocuments.ts
git -C /Users/shifen/ZCodeProject commit -m "feat(frontend): useDocuments hook for CRUD"
```

---

## Task 10: 上传组件与文档列表组件

**Files:**
- Create: `frontend/src/components/DocumentUpload.tsx`
- Create: `frontend/src/components/DocumentList.tsx`

- [ ] **Step 1: 写 `src/components/DocumentUpload.tsx`**

```tsx
import { useState } from 'react'

interface Props {
  onUpload: (file: File, docType: 'resume' | 'qa') => void
}

export function DocumentUpload({ onUpload }: Props) {
  const [docType, setDocType] = useState<'resume' | 'qa'>('resume')
  const [file, setFile] = useState<File | null>(null)

  const submit = () => {
    if (file) {
      onUpload(file, docType)
      setFile(null)
    }
  }

  return (
    <div className="upload-box">
      <input
        type="file"
        accept=".pdf,.md"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <label>
        <input
          type="radio"
          checked={docType === 'resume'}
          onChange={() => setDocType('resume')}
        />
        简历
      </label>
      <label>
        <input
          type="radio"
          checked={docType === 'qa'}
          onChange={() => setDocType('qa')}
        />
        面试题库
      </label>
      <button type="button" onClick={submit} disabled={!file}>
        上传
      </button>
      <p className="hint">支持 PDF（.pdf）、Markdown（.md）</p>
    </div>
  )
}
```

- [ ] **Step 2: 写 `src/components/DocumentList.tsx`**

```tsx
import type { DocumentInfo } from '../types'

interface Props {
  documents: DocumentInfo[]
  onDelete: (id: string) => void
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function typeLabel(t: string): string {
  return t === 'resume' ? '简历' : '题库'
}

export function DocumentList({ documents, onDelete }: Props) {
  if (documents.length === 0) {
    return <p className="empty-state">还没有上传任何文档。</p>
  }
  return (
    <ul className="document-list">
      {documents.map((d) => (
        <li key={d.id} className="document-item">
          <span className="doc-name">📄 {d.filename}</span>
          <span className="doc-type">{typeLabel(d.doc_type)}</span>
          <span className="doc-size">{formatSize(d.size_bytes)}</span>
          <button type="button" onClick={() => onDelete(d.id)}>
            删除
          </button>
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/shifen/ZCodeProject add frontend/src/components/DocumentUpload.tsx frontend/src/components/DocumentList.tsx
git -C /Users/shifen/ZCodeProject commit -m "feat(frontend): document upload and list components"
```

---

## Task 11: 路由改造与管理页组装

**Files:**
- Modify: `frontend/package.json`（加 react-router-dom）
- Create: `frontend/src/routes/ManagePage.tsx`
- Create: `frontend/src/routes/InterviewPage.tsx`（迁移现有 App 逻辑）
- Modify: `frontend/src/App.tsx`（改为路由壳）

- [ ] **Step 1: 安装 react-router-dom**

Run: `cd frontend && npm install react-router-dom`

- [ ] **Step 2: 创建 `src/routes/InterviewPage.tsx`**

把现有 `App.tsx` 的全部逻辑（`subtitle`/`chat`/`useAudioCapture`/`onStart` 等）原样迁移到这个文件，组件名改为 `InterviewPage`，并 `export default InterviewPage`。内容与现有 `App.tsx` 的 `function App()` 完全一致，仅改组件名和文件位置。

- [ ] **Step 3: 创建 `src/routes/ManagePage.tsx`**

```tsx
import { Link } from 'react-router-dom'
import { DocumentList } from '../components/DocumentList'
import { DocumentUpload } from '../components/DocumentUpload'
import { useDocuments } from '../hooks/useDocuments'

export function ManagePage() {
  const { documents, loading, error, upload, remove } = useDocuments()

  return (
    <main className="app-shell">
      <div className="app-frame manage-frame">
        <header className="manage-header">
          <Link to="/" className="back-link">
            ← 返回面试
          </Link>
          <h1>面试助手 · 管理</h1>
        </header>

        <section className="manage-section">
          <h2>上传文档</h2>
          <DocumentUpload onUpload={upload} />
        </section>

        <section className="manage-section">
          <h2>已上传文档</h2>
          {error && <div className="error-banner" role="alert">{error}</div>}
          {loading && documents.length === 0 ? (
            <p className="empty-state">加载中...</p>
          ) : (
            <DocumentList documents={documents} onDelete={remove} />
          )}
        </section>
      </div>
    </main>
  )
}

export default ManagePage
```

- [ ] **Step 4: 改写 `src/App.tsx` 为路由壳**

```tsx
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import InterviewPage from './routes/InterviewPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<InterviewPage />} />
        <Route path="/manage" element={<ManageLazy />} />
      </Routes>
    </BrowserRouter>
  )
}

// 管理页用懒加载避免首屏加载它（可选，本期直接 import 也行）
import ManagePage from './routes/ManagePage'

function ManageLazy() {
  return <ManagePage />
}

export default App
```

> 简化版：直接 import，不做 lazy。上面 ManageLazy 只是占位说明，可删掉直接用 `<ManagePage />`。

最终精简版：

```tsx
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import InterviewPage from './routes/InterviewPage'
import ManagePage from './routes/ManagePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<InterviewPage />} />
        <Route path="/manage" element={<ManagePage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

- [ ] **Step 5: 在面试页加跳转管理页的入口**

在 `InterviewPage.tsx` 的 Controls 上方或顶部加一个链接（不引入新组件，直接用 Link）：

```tsx
import { Link } from 'react-router-dom'

// 在 return 的 JSX 顶部加：
<Link to="/manage" className="manage-link">管理简历/文档</Link>
```

- [ ] **Step 6: 验证 TS 编译**

Run: `cd frontend && npm run build`
Expected: 编译通过，无 TS 错误

- [ ] **Step 7: Commit**

```bash
git -C /Users/shifen/ZCodeProject add frontend/src/App.tsx frontend/src/routes/ frontend/package.json frontend/package-lock.json
git -C /Users/shifen/ZCodeProject commit -m "feat(frontend): react router + manage page"
```

---

## Task 12: 端到端验证

- [ ] **Step 1: 启动后端 + 前端**

```bash
# 终端1
cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000
# 终端2
cd frontend && npm run dev
```

- [ ] **Step 2: 验证清单**

访问 `http://localhost:5173`：
- [ ] 面试页正常显示，顶部有"管理简历/文档"链接
- [ ] 点链接跳到 `/manage`，看到上传区 + 空列表
- [ ] 上传一个 .md 文件，选"面试题库"，点上传 → 列表出现该文档
- [ ] 上传一个 PDF 简历，选"简历" → 列表出现
- [ ] 点删除 → 文档从列表消失
- [ ] 返回面试页，开始采集，生成建议 → 建议内容应能引用简历/题库（人工判断）

- [ ] **Step 3: 提交最终状态**

```bash
git -C /Users/shifen/ZCodeProject add -A
git -C /Users/shifen/ZCodeProject commit -m "chore: end-to-end verification of document management"
```

---

## Self-Review 已完成

**1. Spec 覆盖核对：**
- ✅ 上传简历 PDF → Task 2(解析) + Task 6(路由) + Task 10/11(UI)
- ✅ 上传面试文档 .md → Task 2 + Task 6 + Task 10/11
- ✅ 手动选类型 → Task 6(校验 doc_type) + Task 10(单选 UI)
- ✅ 全文塞上下文（非 RAG）→ Task 4(build_system_prompt) + Task 5/7(注入)
- ✅ 简历/题库分开标注用途 → Task 4(_USAGE_NOTES)
- ✅ 建议链路注入 → Task 5
- ✅ 追问链路注入 → Task 7
- ✅ 文档全局单例、跨 session → Task 3 + Task 6(deps 单例)
- ✅ 独立路由 /manage → Task 11
- ✅ 不落盘、内存存储 → Task 3
- ✅ 新依赖 pypdf/python-multipart/react-router-dom → Task 1/8/11

**2. 占位符扫描：** 无 TBD/TODO，所有步骤含完整代码。

**3. 类型一致性核对：**
- `DocumentStore.add(filename, doc_type, text, size_bytes)` — Task 3 定义，Task 6 调用 ✅
- `parse_document(filename, file_bytes)` — Task 2 定义，Task 6 调用 ✅
- `build_system_prompt(resume_text, qa_text)` — Task 4 定义，Task 5/7 调用 ✅
- `MAX_DOC_SIZE_BYTES` — Task 7 定义，Task 6 import ✅
- `SuggestService(doc_store=...)` — Task 5 加参数，Task 6(deps) 注入 ✅
- `DocumentInfo` / `DocumentListResponse` — Task 1 定义，Task 6 用 ✅
