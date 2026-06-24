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

/** SSE 流式生成建议：逐 token yield。 */
export async function* streamSuggest(sessionId: string): AsyncGenerator<string> {
  const resp = await fetch(`${BASE}/suggest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  })
  yield* readSseStream(resp, '生成失败')
}

export async function postClear(sessionId: string): Promise<void> {
  const resp = await fetch(`${BASE}/clear`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!resp.ok) throw new Error(`清空失败：${resp.status}`)
}

/** SSE 流式追问：逐 token yield。 */
export async function* streamAsk(
  sessionId: string,
  message: string,
): AsyncGenerator<string> {
  const params = new URLSearchParams({ session_id: sessionId, message })
  const resp = await fetch(`${BASE}/ask?${params.toString()}`)
  yield* readSseStream(resp, '追问失败')
}
