/** Token counts the short way: 950, 41k, 1.2M. */
export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
  return n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`
}
