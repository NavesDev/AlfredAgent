import { useQuery } from '@tanstack/react-query'
import type { PDFDocumentProxy } from 'pdfjs-dist'

/** Loads a PDF with pdf.js (WebKitGTK has no viewer of its own); pdf.js stays out of the main
 * bundle until a PDF shows. */
export function usePdf(url: string) {
  return useQuery({
    queryKey: ['pdf', url],
    queryFn: async (): Promise<PDFDocumentProxy> => {
      const [pdfjs, worker] = await Promise.all([
        import('pdfjs-dist'),
        import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
      ])
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default
      return pdfjs.getDocument({ url }).promise
    },
    staleTime: Infinity,
    retry: false,
  })
}
