import type { ReactNode } from 'react'

/** Pill group for a few mutually exclusive options (effort, workspace kind…). */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T
  options: { value: T; label: ReactNode; disabled?: boolean }[]
  onChange: (value: T) => void
  label: string
}) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex rounded-lg border border-white/10 bg-black/30 p-0.5"
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          disabled={o.disabled}
          onClick={() => onChange(o.value)}
          className="rounded-md px-2.5 py-1 text-xs text-gray-400 transition hover:text-gray-200 disabled:opacity-30 aria-checked:bg-white/10 aria-checked:text-gray-100 aria-checked:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className="relative h-5 w-9 shrink-0 rounded-full bg-white/10 transition aria-checked:bg-emerald-400/70"
    >
      <span
        className={`absolute top-0.5 left-0.5 size-4 rounded-full bg-gray-200 shadow transition-transform ${checked ? 'translate-x-4' : ''}`}
      />
    </button>
  )
}

/** Settings row: label and description on the left, control on the right; stacks on phones. */
export function Row({
  title,
  description,
  icon,
  children,
}: {
  title: ReactNode
  description?: ReactNode
  icon?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="flex flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        {icon && (
          <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg border border-white/10 bg-white/[0.03] text-gray-400">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <p className="text-sm text-gray-100">{title}</p>
          {description && <p className="mt-0.5 text-xs text-gray-500">{description}</p>}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">{children}</div>
    </div>
  )
}

/** Titled group of rows separated by hairlines. */
export function Section({
  title,
  description,
  children,
}: {
  title: ReactNode
  description?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-2.5">
      <div>
        <h3 className="text-sm font-medium text-gray-200">{title}</h3>
        {description && <p className="mt-0.5 text-xs text-gray-500">{description}</p>}
      </div>
      <div className="divide-y divide-white/5 rounded-xl border border-white/10 bg-white/[0.02]">
        {children}
      </div>
    </section>
  )
}
