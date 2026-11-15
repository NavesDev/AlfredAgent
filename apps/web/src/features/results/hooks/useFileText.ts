import { useQuery } from '@tanstack/react-query'
import { ApiError } from '../../../api/client'
import { fileUrl } from '../lib/results'

/** A text or Markdown file's content, for the preview. */
export function useFileText(id: number, index: number) {
  return useQuery({
    queryKey: ['result-file', id, index],
    queryFn: async () => {
      const response = await fetch(fileUrl(id, index))
      if (!response.ok) throw new ApiError(response.status, response.statusText)
      return response.text()
    },
    staleTime: Infinity,
  })
}
