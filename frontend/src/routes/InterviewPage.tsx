import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Controls } from '../components/Controls'
import { SubtitlePanel } from '../components/SubtitlePanel'
import { SuggestPanel } from '../components/SuggestPanel'
import { useAudioCapture } from '../hooks/useAudioCapture'
import { useChat } from '../hooks/useChat'
import { useSubtitle } from '../hooks/useSubtitle'

/**
 * 面试助手页：左侧实时字幕 + 右侧建议/追问。
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

  // 生成建议：成功后清空左侧字幕（这轮的话已送走，开始新一轮），
  // 与后端 current_turn_text 清空保持一致。失败不清空，保留字幕方便重试。
  const onSuggest = useCallback(async () => {
    const ok = await chat.generate()
    if (ok) {
      subtitle.clearLines()
    }
  }, [chat, subtitle])

  // 手动输入问题生成建议：走手动模式（后端不动语音累积）。
  // 成功后清左侧显示（手动问题独立成轮，与语音字幕分离）。
  const onManualAsk = useCallback(
    async (question: string) => {
      const ok = await chat.generate(question)
      if (ok) {
        subtitle.clearLines()
      }
    },
    [chat, subtitle],
  )

  const onClear = useCallback(async () => {
    await chat.clear()
    subtitle.clearLines()
  }, [chat, subtitle])

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
          onSuggest={onSuggest}
          onClear={onClear}
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
            onManualAsk={onManualAsk}
          />
          <SuggestPanel
            suggestion={chat.suggestion}
            loading={chat.loading}
            streaming={chat.streaming}
            followups={chat.followups}
            error={chat.error}
            onAsk={chat.ask}
          />
        </section>
      </div>
    </main>
  )
}

export default InterviewPage
