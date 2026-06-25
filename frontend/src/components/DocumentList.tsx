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

/**
 * 文档列表：名称 / 类型 / 大小 / 删除按钮。
 */
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
