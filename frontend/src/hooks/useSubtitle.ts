import { useCallback, useRef, useState } from 'react'
import { AsrSocket } from '../api/asrSocket'
import { clearSubtitle, removeSubtitleLine } from '../api/chat'
import type { SubtitleLine } from '../types'

/**
 * 管理字幕：连 ASR WebSocket，维护当前识别中的句子 + 定稿历史。
 *
 * 字幕操作分两类：
 * - 本地清空（clearLines）：仅前端清显示，配合生成建议后重置，不碰后端。
 * - 同步操作（removeLine / clearAll）：同时改后端 current_turn_text，
 *   保证删除/清空后生成建议时不会把已删内容送给 LLM。
 */
export function useSubtitle() {
  const [lines, setLines] = useState<SubtitleLine[]>([])
  const [currentPartial, setCurrentPartial] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [error, setError] = useState('')
  const socketRef = useRef<AsrSocket | null>(null)

  const connect = useCallback(() => {
    const socket = new AsrSocket({
      onReady: (sid) => setSessionId(sid),
      onPartial: (text) => setCurrentPartial(text),
      onFinal: (text) => {
        setCurrentPartial('')
        setLines((prev) => [...prev, { text, isFinal: true }])
      },
      onError: (msg) => setError(msg),
    })
    socket.connect()
    socketRef.current = socket
  }, [])

  const sendAudio = useCallback((buf: ArrayBuffer) => {
    socketRef.current?.sendAudio(buf)
  }, [])

  const close = useCallback(() => {
    socketRef.current?.close()
    socketRef.current = null
  }, [])

  // 仅前端清空显示（生成建议后调用，后端那轮已经送走并清过了）。
  const clearLines = useCallback(() => {
    setLines([])
    setCurrentPartial('')
  }, [])

  // 同步后端删除某一行字幕（删完后端那行，本地也删）。
  const removeLine = useCallback(
    async (index: number) => {
      if (!sessionId) return
      try {
        await removeSubtitleLine(sessionId, index)
        setLines((prev) => prev.filter((_, i) => i !== index))
      } catch (e) {
        setError((e as Error).message)
      }
    },
    [sessionId],
  )

  // 同步后端清空当前轮次所有字幕（后端 current_turn_text 清空，本地也清）。
  const clearAll = useCallback(async () => {
    if (!sessionId) return
    try {
      await clearSubtitle(sessionId)
      setLines([])
      setCurrentPartial('')
    } catch (e) {
      setError((e as Error).message)
    }
  }, [sessionId])

  return {
    lines,
    currentPartial,
    sessionId,
    error,
    connect,
    sendAudio,
    close,
    clearLines,
    removeLine,
    clearAll,
  }
}
