/** 后端对话 + 字幕 API 客户端。 */

const BASE = '/api'

/** SSE 流式读取通用工具：把 fetch 的 SSE 响应逐 token yield。 */
async function* readSseStream(
  resp: Response,
  failMsg: string,
): AsyncGenerator<string> {
  if (!resp.ok || !resp.body) throw new Error(`${failMsg}：${resp.status}`)
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const payload = JSON.parse(line.slice(6))
          if (payload.delta) yield payload.delta as string
          else if (payload.error) throw new Error(payload.error)
        } catch {
          // 忽略不完整的 JSON
        }
      }
    }
  }
}

/** 发送一条消息（或字幕区全部内容）给 LLM，流式返回回复。 */
export async function* sendChat(
  sessionId: string,
  body: { message?: string; send_subtitles?: boolean },
): AsyncGenerator<string> {
  const resp = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, ...body }),
  })
  yield* readSseStream(resp, '对话失败')
}

/** 清空整个对话历史（字幕区不动）。 */
export async function resetChat(sessionId: string): Promise<void> {
  const resp = await fetch(`${BASE}/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!resp.ok) throw new Error(`重置失败：${resp.status}`)
}

/** 删除字幕区某一行。返回剩余行。 */
export async function removeSubtitleLine(
  sessionId: string,
  lineIndex: number,
): Promise<string[]> {
  const resp = await fetch(`${BASE}/subtitle/remove-line`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, line_index: lineIndex }),
  })
  if (!resp.ok) throw new Error(`删除失败：${resp.status}`)
  const data = await resp.json()
  return data.remaining_lines as string[]
}

/** 清空字幕区（不影响对话历史）。 */
export async function clearSubtitle(sessionId: string): Promise<void> {
  const resp = await fetch(`${BASE}/subtitle/clear`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!resp.ok) throw new Error(`清空字幕失败：${resp.status}`)
}
