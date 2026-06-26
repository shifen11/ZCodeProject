import { Link } from 'react-router-dom'

interface Props {
  isCapturing: boolean
  onStart: () => void
  onStop: () => void
  /** 侧边栏是否收起 */
  sidebarCollapsed: boolean
  onToggleSidebar: () => void
}

/**
 * 顶部控制栏：侧边栏开关 + 品牌 + 采集开关 + 管理入口。
 */
export function Controls({
  isCapturing,
  onStart,
  onStop,
  sidebarCollapsed,
  onToggleSidebar,
}: Props) {
  return (
    <header className="topbar">
      <button
        type="button"
        className="sidebar-toggle"
        onClick={onToggleSidebar}
        aria-label={sidebarCollapsed ? '展开会话列表' : '收起会话列表'}
        title={sidebarCollapsed ? '展开会话列表' : '收起会话列表'}
      >
        {sidebarCollapsed ? '☰' : '✕'}
      </button>
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
      <Link to="/manage" className="secondary-control manage-btn">
        📂 管理
      </Link>
    </header>
  )
}
