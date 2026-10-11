export type Step = { ts: number; kind: 'text' | 'tool'; content: string; detail: string | null }

/** One exchange: what was heard, what the agent did, what it answered, and the timings. */
export type Turn = {
  id: number
  heardAt: number
  source: 'voice' | 'web' | null
  userText: string | null
  /** Recording stop → transcript ready (seconds), voice only. */
  sttS: number | null
  steps: Step[]
  /** Transcript → first audio out (seconds). */
  firstSpeechS: number | null
  /** Transcript → full reply (seconds). */
  replyS: number | null
  summary: string | null
  reply: string | null
  error: string | null
}

export type TranscriptState = {
  turns: Turn[]
  transcribingAt: number | null
  nextId: number
}
