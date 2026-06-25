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


def test_list_does_not_lose_metadata():
    """list 返回完整 Document（含 text），元信息可断言。"""
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
