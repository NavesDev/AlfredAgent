import { useMutation } from '@tanstack/react-query'
import { api } from '../../../api/client'
import type { PresentMode } from '../../../api/events'

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

/** Show a result again, or open one of its files (the server opens it on this computer). */
export function useResultActions() {
  const present = useMutation({
    mutationFn: ({ id, mode }: { id: number; mode: PresentMode }) =>
      api<void>(`/api/results/${id}/present`, json({ mode })),
  })
  const open = useMutation({
    mutationFn: ({ id, index, reveal }: { id: number; index: number; reveal: boolean }) =>
      api<void>(`/api/results/${id}/files/${index}/open`, json({ reveal })),
  })
  return { present, open }
}
