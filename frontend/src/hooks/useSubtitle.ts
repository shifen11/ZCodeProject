import { useCallback, useRef, useState } from 'react'
import { AsrSocket } from '../api/asrSocket'
import { clearSubtitle, removeSubtitleLine } from '../api/chat'
import type { SubtitleLine } from '../types'

/**
 * 管理字幕：连 ASR WebSocket，维护当前识别中的句子 + 定稿历史。
 *
 * sessionId 由外部传入（useSession 统一管理），WS 连接时复用，
 * 使字幕进同一个会话（对话/字幕共享）。
 *
 * 字幕操作分两类：
 * - 本地清空（clearLines）：仅前端清显示，发送字幕后重置，不碰后端。
 * - 同步操作（removeLine / clearAll）：同时改后端 subtitle_lines。
 */
export function useSubtitle(sessionId: string) {
  const [lines, setLines] = useState<SubtitleLine[]>([])
  const [currentPartial, setCurrentPartial] = useState('')
  const [error, setError] = useState('')
  const socketRef = useRef<AsrSocket | null>(null)

  const connect = useCallback(() => {
    const socket = new AsrSocket({
      onReady: () => {
        // sessionId 由外部管理，这里无需处理
      },
      onPartial: (text) => setCurrentPartial(text),
      onFinal: (text) => {
        setCurrentPartial('')
        setLines((prev) => [...prev, { text, isFinal: true }])
      },
      onError: (msg) => setError(msg),
    })
    socket.connect(sessionId)
    socketRef.current = socket
  }, [sessionId])

  const sendAudio = useCallback((buf: ArrayBuffer) => {
    socketRef.current?.sendAudio(buf)
  }, [])

  const close = useCallback(() => {
    socketRef.current?.close()
    socketRef.current = null
  }, [])

  // 仅前端清空显示（发送字幕后调用，后端那批已经消费并清过了）。
  const clearLines = useCallback(() => {
    setLines([])
    setCurrentPartial('')
  }, [])

  // 同步后端删除某一行字幕。
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

  // 同步后端清空字幕区。
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
    error,
    connect,
    sendAudio,
    close,
    clearLines,
    removeLine,
    clearAll,
  }
}
