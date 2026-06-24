import { useEffect, useRef } from 'react'
import type { SubtitleLine } from '../types'

interface Props {
  lines: SubtitleLine[]
  currentPartial: string
}

export function SubtitlePanel({ lines, currentPartial }: Props) {
  // 自动滚到底部
  const bottomRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines, currentPartial])

  return (
    <section className="panel-card subtitle-card" aria-label="实时字幕">
      <header className="panel-header">
        <h2>实时字幕</h2>
        <span>自动滚动</span>
      </header>
      <div className="subtitle-content">
        {lines.length === 0 && !currentPartial && (
          <p className="empty-state">点“开始采集”后，面试官的话会出现在这里。</p>
        )}
        {lines.map((line, index) => (
          <p key={index} className="subtitle-line">{line.text}</p>
        ))}
        {currentPartial && (
          <p className="subtitle-partial">
            <span>识别中</span>
            {currentPartial}
          </p>
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  )
}
