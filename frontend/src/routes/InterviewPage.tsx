import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ChatPanel } from '../components/ChatPanel'
import { Controls } from '../components/Controls'
import { SessionSidebar } from '../components/SessionSidebar'
import { SubtitlePanel } from '../components/SubtitlePanel'
import { useAudioCapture } from '../hooks/useAudioCapture'
import { useChat } from '../hooks/useChat'
import { useSessions } from '../hooks/useSessions'
import { useSubtitle } from '../hooks/useSubtitle'

/**
 * 面试助手页：左侧会话列表 + 字幕区 + 右侧对话区。
 * 像 ChatGPT 那样支持多会话切换。
 */
function InterviewPage() {
  const sessions = useSessions()
  const sessionId = sessions.currentId
  const subtitle = useSubtitle(sessionId)
  const chat = useChat(sessionId)

  const handleChunk = useCallback(
    (buf: ArrayBuffer) => subtitle.sendAudio(buf),
    [subtitle],
  )
  const { isCapturing, start, stop, error: captureError } =
    useAudioCapture(handleChunk)

  const onStart = async () => {
    subtitle.connect(sessionId)
    await start()
  }
  const onStop = () => {
    stop()
    subtitle.close()
  }

  // 发送字幕后刷新会话列表（标题可能因首条消息变化）
  const onSendSubtitles = useCallback(async () => {
    const text = subtitle.lines.map((l) => l.text).join('\n').trim()
    if (!text) return
    const ok = await chat.sendSubtitles(text)
    if (ok) {
      subtitle.clearLines()
      sessions.refresh()
    }
  }, [chat, subtitle, sessions])

  const onManualSend = useCallback(
    async (message: string) => {
      await chat.send(message)
      sessions.refresh()
    },
    [chat, sessions],
  )

  const onReset = useCallback(async () => {
    await chat.reset()
    sessions.refresh()
  }, [chat, sessions])

  return (
    <main className="app-shell">
      <div className="app-frame app-frame-with-sidebar">
        <SessionSidebar
          sessions={sessions.sessions}
          currentId={sessionId}
          onSelect={sessions.switchTo}
          onCreate={sessions.createNew}
          onDelete={sessions.remove}
        />
        <div className="app-main">
          <div className="top-nav">
            <Link to="/manage" className="manage-link">
              管理简历/文档
            </Link>
          </div>
          <Controls
            isCapturing={isCapturing}
            onStart={onStart}
            onStop={onStop}
          />
          {(captureError || subtitle.error || sessions.error) && (
            <div className="error-banner" role="alert">
              {captureError || subtitle.error || sessions.error}
            </div>
          )}
          <section className="workspace" aria-label="面试辅助工作区">
            <SubtitlePanel
              lines={subtitle.lines}
              currentPartial={subtitle.currentPartial}
              onRemoveLine={subtitle.removeLine}
              onClearAll={subtitle.clearAll}
              onSendSubtitles={onSendSubtitles}
            />
            <ChatPanel
              messages={chat.messages}
              streaming={chat.streaming}
              loading={chat.loading}
              error={chat.error}
              onSend={onManualSend}
              onReset={onReset}
            />
          </section>
        </div>
      </div>
    </main>
  )
}

export default InterviewPage
