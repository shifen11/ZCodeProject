interface Props {
  isCapturing: boolean
  onStart: () => void
  onStop: () => void
}

/**
 * 顶部控制栏：只管音频采集开关。
 * （发送字幕/重置对话等操作放在各自面板里，职责更清晰。）
 */
export function Controls({ isCapturing, onStart, onStop }: Props) {
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
    </header>
  )
}
