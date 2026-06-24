import { useState } from 'react'
import type { ChatMessage } from '../types'

interface Props {
  suggestion: string
  loading: boolean
  streaming: string
  followups: ChatMessage[]
  error: string
  onAsk: (msg: string) => void
}

export function SuggestPanel({
  suggestion,
  loading,
  streaming,
  followups,
  error,
  onAsk,
}: Props) {
  const [input, setInput] = useState('')
  const send = () => {
    if (input.trim()) {
      onAsk(input.trim())
      setInput('')
    }
  }

  return (
    <section className="panel-card suggest-card" aria-label="回答建议">
      <header className="panel-header">
        <h2>回答建议</h2>
        <span>基于当前字幕</span>
      </header>
      <div className="suggestion-content">
        {loading ? (
          <p className="empty-state">生成中...</p>
        ) : suggestion ? (
          <div className="suggestion-box">{suggestion}</div>
        ) : (
          <p className="empty-state">
            面试官问完后，点“生成建议”获取回答思路。
          </p>
        )}
        {error && <p className="suggestion-error">{error}</p>}
        {streaming && (
          <p className="suggestion-streaming">{streaming}</p>
        )}
        {followups.length > 0 && <hr className="followup-divider" />}
        {followups.map((m, i) => (
          <p
            key={i}
            className={`followup-message ${m.role === 'user' ? 'is-user' : 'is-assistant'}`}
          >
            <strong>{m.role === 'user' ? '你' : '助手'}：</strong>
            <span>{m.content}</span>
          </p>
        ))}
      </div>
      <form
        className="ask-form"
        onSubmit={(event) => {
          event.preventDefault()
          send()
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="追问（如：再详细点 / 换个角度）"
        />
        <button type="submit">发送</button>
      </form>
    </section>
  )
}
