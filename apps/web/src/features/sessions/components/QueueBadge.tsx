/** Tasks still lined up for this session after the current one, as a "+N" on the drawing. */
export function QueueBadge({ count }: { count: number }) {
  if (count <= 0) return null
  const label = count === 1 ? '1 tarefa esperando' : `${count} tarefas esperando`
  return (
    <span
      title={label}
      aria-label={label}
      className="absolute -top-1 -right-3 rounded-full border border-white/15 bg-[#0c0c0e] px-1 font-mono text-[9px] leading-3 text-gray-300"
    >
      +{count}
    </span>
  )
}
