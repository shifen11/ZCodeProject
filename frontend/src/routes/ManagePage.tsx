import { Link } from 'react-router-dom'
import { DocumentList } from '../components/DocumentList'
import { DocumentUpload } from '../components/DocumentUpload'
import { useDocuments } from '../hooks/useDocuments'

/**
 * 管理页：上传简历(PDF)/面试题库(.md)，查看并删除已上传文档。
 */
function ManagePage() {
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
          {error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}
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
