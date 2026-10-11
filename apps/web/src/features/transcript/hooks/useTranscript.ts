import { useReducer } from 'react'
import { useEvents } from '../../../hooks/useEvents'
import { initialTranscript, reduceTranscript } from '../lib/turns'

export function useTranscript() {
  const [state, dispatch] = useReducer(reduceTranscript, initialTranscript)
  useEvents(dispatch)
  return state.turns
}
