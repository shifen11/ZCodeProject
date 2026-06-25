import { useEffect, useState } from 'react'
import { createSession } from '../api/chat'

/**
 * 会话管理：页面挂载时创建一个会话，返回 sessionId。
 * 让对话/字幕不依赖音频采集——开不开麦都能用。
 */
export function useSession() {
  const [sessionId, setSessionId] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    createSession()
      .then((sid) => {
        if (!cancelled) setSessionId(sid)
      })
      .catch((e) => {
        if (!cancelled) setError((e as Error).message)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { sessionId, error }
}
