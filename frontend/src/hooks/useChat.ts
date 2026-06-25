import { useCallback, useState } from 'react'
import { resetChat, sendChat } from '../api/chat'
import type { ChatMessage } from '../types'

/**
 * 纯聊天：一个不断累积的对话历史。
 * - send(message)：手打一条消息，流式追加 user+assistant。
 * - sendSubtitles()：把字幕区全部内容作为一条消息发出。
 * - reset()：清空整个对话历史。
 */
export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const sendStream = useCallback(
    async (body: { message?: string; send_subtitles?: boolean }): Promise<boolean> => {
      if (!sessionId) return false
      setLoading(true)
      setError('')
      setStreaming('')
      // 先把 user 消息加进显示（字幕发送时这里先空着，让后端消费后再不补，
      // 因为字幕区在前端已可见，避免重复显示）
      if (body.message) {
        setMessages((prev) => [...prev, { role: 'user', content: body.message! }])
      }
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
    (message: string) => sendStream({ message }),
    [sendStream],
  )

  const sendSubtitles = useCallback(
    () => sendStream({ send_subtitles: true }),
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
