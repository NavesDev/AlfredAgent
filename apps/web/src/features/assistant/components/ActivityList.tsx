import type { Activity } from '../hooks/useActivity'

/** Latest step bright with a pulse, earlier ones fading above it. */
export function ActivityList({ items }: { items: Activity[] }) {
  return (
    <ul
      className="flex min-h-16 flex-col items-center justify-end gap-1 text-sm"
      aria-live="polite"
    >
      {items.map((item, i) => {
        const latest = i === items.length - 1
        return (
          <li
            key={item.id}
            className={`flex max-w-xl items-center gap-2 truncate transition-opacity duration-500 ${
              latest ? 'text-amber-200' : 'text-gray-500 opacity-60'
            }`}
          >
            {latest && (
              <span className="size-1.5 shrink-0 animate-ping rounded-full bg-amber-300" />
            )}
            <span className="truncate">{item.text}…</span>
          </li>
        )
      })}
    </ul>
  )
}
