import { useCallback, useState } from 'react'
import { postClear, streamAsk, streamSuggest } from '../api/chat'
import type { ChatMessage } from '../types'

/**
 * 管理建议 + 追问：generate 流式生成建议，ask 流式追问，clear 清空。
 */
export function useChat(sessionId: string) {
  const [suggestion, setSuggestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState('')
  const [followups, setFollowups] = useState<ChatMessage[]>([])
  const [error, setError] = useState('')

  // 生成建议：流式返回，逐 token 累积显示。成功返回 true。
  // question 非空时走手动输入模式（不读/不清语音字幕）。
  const generate = useCallback(async (question?: string): Promise<boolean> => {
    if (!sessionId) return false
    setLoading(true)
    setError('')
    setSuggestion('')
    try {
      let acc = ''
      for await (const delta of streamSuggest(sessionId, question)) {
        acc += delta
        setSuggestion(acc)
      }
      return true
    } catch (e) {
      setError((e as Error).message)
      return false
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  const ask = useCallback(
    async (message: string) => {
      if (!sessionId) return
      setFollowups((prev) => [...prev, { role: 'user', content: message }])
      setStreaming('')
      try {
        let acc = ''
        for await (const delta of streamAsk(sessionId, message)) {
          acc += delta
          setStreaming(acc)
        }
        setFollowups((prev) => [...prev, { role: 'assistant', content: acc }])
      } catch (e) {
        setFollowups((prev) => [
          ...prev,
          { role: 'assistant', content: `（出错）${(e as Error).message}` },
        ])
      } finally {
        setStreaming('')
      }
    },
    [sessionId],
  )

  const clear = useCallback(async () => {
    if (!sessionId) return
    await postClear(sessionId)
    setSuggestion('')
    setFollowups([])
    setError('')
  }, [sessionId])

  return { suggestion, loading, streaming, followups, error, generate, ask, clear }
}
