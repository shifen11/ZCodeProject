interface Props {
  isCapturing: boolean
  onStart: () => void
  onStop: () => void
  onSuggest: () => void
  onClear: () => void
}

export function Controls({
  isCapturing,
  onStart,
  onStop,
  onSuggest,
  onClear,
}: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-icon" aria-hidden="true">✦</span>
        <strong>面试助手</strong>
      </div>
      <div
        className={`capture-status ${isCapturing ? 'is-active' : ''}`}
        role="status"
        aria-live="polite"
      >
        <span aria-hidden="true" className="status-dot" />
        {isCapturing ? '正在采集' : '等待采集'}
      </div>
      {isCapturing ? (
        <button className="primary-control" onClick={onStop}>⏹ 停止采集</button>
      ) : (
        <button className="primary-control" onClick={onStart}>▶ 开始采集</button>
      )}
      <button className="accent-control" onClick={onSuggest}>✨ 生成建议</button>
      <button className="secondary-control" onClick={onClear}>🗑 清空上下文</button>
    </header>
  )
}
