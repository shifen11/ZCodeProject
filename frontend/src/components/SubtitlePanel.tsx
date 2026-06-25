import { useEffect, useRef, useState } from 'react'
import type { SubtitleLine } from '../types'

interface Props {
  lines: SubtitleLine[]
  currentPartial: string
  onRemoveLine: (index: number) => void
  onClearAll: () => void
  /** 手动输入面试官问题，发送后直接生成建议（不经过语音识别）。 */
  onManualAsk: (question: string) => void
}

export function SubtitlePanel({
  lines,
  currentPartial,
  onRemoveLine,
  onClearAll,
  onManualAsk,
}: Props) {
  // 自动滚到底部
  const bottomRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines, currentPartial])

  const [manualInput, setManualInput] = useState('')
  const sendManual = () => {
    const q = manualInput.trim()
    if (q) {
      onManualAsk(q)
      setManualInput('')
    }
  }

  return (
    <section className="panel-card subtitle-card" aria-label="实时字幕">
      <header className="panel-header">
        <h2>实时字幕</h2>
        {lines.length > 0 && (
          <button type="button" className="text-btn" onClick={onClearAll}>
            清空字幕
          </button>
        )}
      </header>
      <div className="subtitle-content">
        {lines.length === 0 && !currentPartial && (
          <p className="empty-state">
            点"开始采集"后，面试官的话会出现在这里。也可在下方手动输入问题。
          </p>
        )}
        {lines.map((line, index) => (
          <div key={index} className="subtitle-line-row">
            <p className="subtitle-line">{line.text}</p>
            <button
              type="button"
              className="line-remove-btn"
              aria-label="删除该行"
              onClick={() => onRemoveLine(index)}
            >
              ×
            </button>
          </div>
        ))}
        {currentPartial && (
          <p className="subtitle-partial">
            <span>识别中</span>
            {currentPartial}
          </p>
        )}
        <div ref={bottomRef} />
      </div>
      <form
        className="manual-input-form"
        onSubmit={(e) => {
          e.preventDefault()
          sendManual()
        }}
      >
        <input
          aria-label="手动输入面试官问题"
          value={manualInput}
          onChange={(e) => setManualInput(e.target.value)}
          placeholder="手动输入问题，回车生成建议"
        />
        <button type="submit">发送</button>
      </form>
    </section>
  )
}
