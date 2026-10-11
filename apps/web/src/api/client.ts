// Thin fetch helpers for /api; types come from the generated schema.ts.

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new ApiError(response.status, body?.detail ?? response.statusText)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}
