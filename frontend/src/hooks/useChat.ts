import { useCallback, useState } from 'react'
import { resetChat, sendChat } from '../api/chat'
import type { ChatMessage } from '../types'

/**
 * 纯聊天：一个不断累积的对话历史。
 * - send(message)：手打一条消息，流式追加 user+assistant。
 * - sendSubtitles(subtitleText)：把字幕区全部内容作为一条 user 消息发出。
 *   字幕文本会像手打一样显示在右侧对话区。
 * - reset()：清空整个对话历史。
 */
export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 流式发送：把 user 消息先显示，再请求后端拿流式 assistant 回复。
  const sendStream = useCallback(
    async (
      body: { message?: string; send_subtitles?: boolean },
      displayText: string,
    ): Promise<boolean> => {
      if (!sessionId) return false
      setLoading(true)
      setError('')
      setStreaming('')
      // 先把 user 消息显示出来（手打或字幕都一样展示）
      setMessages((prev) => [...prev, { role: 'user', content: displayText }])
      try {
        let acc = ''
        for await (const delta of sendChat(sessionId, body)) {
          acc += delta
          setStreaming(acc)
        }
        setMessages((prev) => [...prev, { role: 'assistant', content: acc }])
        return true
      } catch (e) {
        setError((e as Error).message)
        return false
      } finally {
        setStreaming('')
        setLoading(false)
      }
    },
    [sessionId],
  )

  const send = useCallback(
    (message: string) => sendStream({ message }, message),
    [sendStream],
  )

  // 发送字幕：displayText 是要显示的字幕文本（发送前从字幕区读出），
  // body 用 send_subtitles 让后端消费字幕区。
  const sendSubtitles = useCallback(
    (subtitleText: string) => sendStream({ send_subtitles: true }, subtitleText),
    [sendStream],
  )

  const reset = useCallback(async () => {
    if (!sessionId) return
    setError('')
    try {
      await resetChat(sessionId)
      setMessages([])
    } catch (e) {
      setError((e as Error).message)
    }
  }, [sessionId])

  return { messages, streaming, loading, error, send, sendSubtitles, reset }
}
