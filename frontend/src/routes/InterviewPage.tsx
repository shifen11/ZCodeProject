import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ChatPanel } from '../components/ChatPanel'
import { Controls } from '../components/Controls'
import { SubtitlePanel } from '../components/SubtitlePanel'
import { useAudioCapture } from '../hooks/useAudioCapture'
import { useChat } from '../hooks/useChat'
import { useSubtitle } from '../hooks/useSubtitle'

/**
 * 面试助手页：左侧字幕区（采集）+ 右侧对话区（和 GLM 聊）。
 */
function InterviewPage() {
  const subtitle = useSubtitle()
  const chat = useChat(subtitle.sessionId)

  const handleChunk = useCallback(
    (buf: ArrayBuffer) => subtitle.sendAudio(buf),
    [subtitle],
  )
  const { isCapturing, start, stop, error: captureError } =
    useAudioCapture(handleChunk)

  const onStart = async () => {
    subtitle.connect()
    await start()
  }
  const onStop = () => {
    stop()
    subtitle.close()
  }

  // 发送字幕：把字幕区全部内容发给 LLM。成功后清前端字幕（后端已清）。
  const onSendSubtitles = useCallback(async () => {
    const ok = await chat.sendSubtitles()
    if (ok) {
      subtitle.clearLines()
    }
  }, [chat, subtitle])

  // 手动输入：直接发给 LLM（不进字幕区）。
  const onManualSend = useCallback(
    (message: string) => {
      chat.send(message)
    },
    [chat],
  )

  return (
    <main className="app-shell">
      <div className="app-frame">
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
        {(captureError || subtitle.error) && (
          <div className="error-banner" role="alert">
            {captureError || subtitle.error}
          </div>
        )}
        <section className="workspace" aria-label="面试辅助工作区">
          <SubtitlePanel
            lines={subtitle.lines}
            currentPartial={subtitle.currentPartial}
            onRemoveLine={subtitle.removeLine}
            onClearAll={subtitle.clearAll}
            onSendSubtitles={onSendSubtitles}
            onManualSend={onManualSend}
          />
          <ChatPanel
            messages={chat.messages}
            streaming={chat.streaming}
            loading={chat.loading}
            error={chat.error}
            onSend={chat.send}
            onReset={chat.reset}
          />
        </section>
      </div>
    </main>
  )
}

export default InterviewPage
