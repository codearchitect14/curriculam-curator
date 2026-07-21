/**
 * All frontend API calls to the backend.
 */

const BACKEND_ERROR =
  'Backend not reachable — start with: cd backend && uvicorn api:app --reload --port 8417'

/**
 * Parse SSE stream from a fetch response.
 */
async function parseSSEStream(response, onProgress, onResult, onError) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      if (!part.trim()) continue

      let eventType = 'message'
      let data = ''

      for (const line of part.split('\n')) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          data = line.slice(5).trim()
        }
      }

      if (!data) continue

      try {
        const parsed = JSON.parse(data)
        if (eventType === 'progress') {
          onProgress(parsed)
        } else if (eventType === 'result') {
          onResult(parsed)
        } else if (eventType === 'error') {
          onError(parsed.message || 'Unknown error')
        }
      } catch {
        onError('Failed to parse server response')
      }
    }
  }
}

/**
 * Check backend connectivity.
 */
export async function checkHealth() {
  try {
    const response = await fetch('/api/health')
    if (!response.ok) {
      throw new Error(BACKEND_ERROR)
    }
    return await response.json()
  } catch {
    throw new Error(BACKEND_ERROR)
  }
}

/**
 * Stream curriculum generation with live progress updates.
 * @param {object} persona - Full persona object (required for custom personas)
 * @param {function} onProgress
 * @param {function} onResult
 * @param {function} onError
 * @param {{ signal?: AbortSignal, personaId?: string|null }} options
 */
export async function streamCurriculum(
  persona,
  onProgress,
  onResult,
  onError,
  options = {}
) {
  const { signal, personaId } = options
  try {
    const url = personaId
      ? `/api/curriculum/stream?persona_id=${encodeURIComponent(personaId)}`
      : `/api/curriculum/stream?persona=${encodeURIComponent(JSON.stringify(persona))}`
    const response = await fetch(url, { signal })

    if (!response.ok) {
      let message = BACKEND_ERROR
      try {
        const err = await response.json()
        message = err.error || message
      } catch {
        // use default
      }
      onError(message)
      return
    }

    await parseSSEStream(response, onProgress, onResult, onError)
  } catch (err) {
    if (err.name === 'AbortError') {
      return
    }
    onError(BACKEND_ERROR)
  }
}

/**
 * Fetch all test personas.
 */
export async function getTestPersonas() {
  try {
    const response = await fetch('/api/test-personas')
    if (!response.ok) {
      throw new Error(BACKEND_ERROR)
    }
    return await response.json()
  } catch {
    throw new Error(BACKEND_ERROR)
  }
}

/**
 * Ask a follow-up question about a curriculum.
 */
export async function askFollowup(persona, curriculum, question) {
  try {
    const response = await fetch('/api/followup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ persona, curriculum, question }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.error || BACKEND_ERROR)
    }
    const data = await response.json()
    return data.answer
  } catch (e) {
    throw new Error(e.message || BACKEND_ERROR)
  }
}

/**
 * Evaluate a curriculum against a persona.
 */
export async function evaluateCurriculum(persona, curriculum) {
  try {
    const response = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ persona, curriculum }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.error || BACKEND_ERROR)
    }
    return await response.json()
  } catch (e) {
    throw new Error(e.message || BACKEND_ERROR)
  }
}
