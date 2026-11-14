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
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-full bg-well p-[3px]">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          disabled={o.disabled}
          onClick={() => onChange(o.value)}
          className="rounded-full px-3 py-1.5 text-[12.5px] font-medium text-ink-2 transition hover:text-ink disabled:opacity-30 aria-checked:bg-fill-on aria-checked:text-ink"
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
      className="relative h-[30px] w-[50px] shrink-0 rounded-full bg-[rgb(120_120_128/0.36)] transition aria-checked:bg-apple-green"
    >
      <span
        className={`absolute top-[2px] left-[2px] size-[26px] rounded-full bg-white shadow-[0_2px_6px_rgba(0,0,0,0.3)] transition-transform ${checked ? 'translate-x-5' : ''}`}
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
    <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        {icon && (
          <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-[#636366] text-white">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <p className="text-sm">{title}</p>
          {description && <p className="mt-0.5 text-xs text-ink-2">{description}</p>}
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
        <h3 className="text-[13px] font-semibold tracking-wide text-ink-2 uppercase">{title}</h3>
        {description && <p className="mt-0.5 text-xs text-ink-3">{description}</p>}
      </div>
      <div className="divide-y divide-hairline overflow-hidden rounded-[18px] bg-well">
        {children}
      </div>
    </section>
  )
}
