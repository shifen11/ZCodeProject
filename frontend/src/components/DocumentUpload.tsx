import { useState } from 'react'

interface Props {
  onUpload: (file: File, docType: 'resume' | 'qa') => void
}

/**
 * 文档上传区：文件选择 + 类型单选（简历/题库）+ 上传按钮。
 */
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
      <div className="doc-type-radios">
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
      </div>
      <button type="button" onClick={submit} disabled={!file}>
        上传
      </button>
      <p className="hint">支持 PDF（.pdf）、Markdown（.md）</p>
    </div>
  )
}
