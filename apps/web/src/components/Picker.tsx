import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { Check, ChevronDown } from './icons'

// The panel's dropdown (glass list, grouped, a hint per option), after
// @notra/claude-model-selector (shadcn registry). Optionally takes any other value typed in.

export type PickerOption = { id: string; label: string; hint?: string; group?: string }

type Props = {
  value: string
  onChange: (value: string) => void
  options: PickerOption[]
  label: string
  /** Shown when the value is empty and no option has the empty id. */
  placeholder?: string
  compact?: boolean
  mono?: boolean
  /** Free field under the list for values the options leave out. */
  custom?: { label: string; placeholder: string }
}

export function Picker({
  value,
  onChange,
  options,
  label,
  placeholder,
  compact,
  mono,
  custom,
}: Props) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [typed, setTyped] = useState('')
  const root = useRef<HTMLDivElement>(null)
  const listId = useId()
  const current = options.find((o) => o.id === value)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => !root.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const pick = (id: string) => {
    onChange(id)
    setOpen(false)
  }
  const toggle = () => {
    setActive(
      Math.max(
        0,
        options.findIndex((o) => o.id === value),
      ),
    )
    setOpen((o) => !o)
  }
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') return setOpen(false)
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault()
      return toggle()
    }
    if (!open) return
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const step = e.key === 'ArrowDown' ? 1 : -1
      setActive((i) => (i + step + options.length) % options.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      pick(options[active].id)
    }
  }

  let shown: ReactNode = <span className="text-ink-3">{placeholder}</span>
  if (current)
    shown = <span className={mono && current.id ? 'font-mono' : ''}>{current.label}</span>
  else if (value) shown = <span className="font-mono">{value}</span>

  return (
    <div ref={root} className="relative" onKeyDown={onKey}>
      <button
        type="button"
        aria-label={label}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={toggle}
        className={`flex w-full items-center gap-2 rounded-xl bg-well text-left text-ink outline-none hover:bg-fill focus-visible:ring-2 focus-visible:ring-apple-blue/60 aria-expanded:bg-fill ${compact ? 'px-2 py-1 text-xs' : 'px-2.5 py-1.5 text-sm'}`}
      >
        <span className="min-w-0 flex-1 truncate">{shown}</span>
        <ChevronDown
          className={`size-3.5 shrink-0 text-ink-3 transition ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="absolute right-0 left-0 z-20 mt-1.5 min-w-64 glass rounded-2xl p-1.5">
          <ul
            id={listId}
            role="listbox"
            aria-label={label}
            className="flex max-h-80 flex-col overflow-y-auto"
          >
            {options.map((o, i) => (
              <li key={o.id || 'default'} role="presentation">
                {o.group && o.group !== options[i - 1]?.group && (
                  <p className="px-2.5 pt-2 pb-1 text-[10px] font-medium tracking-wider text-ink-3 uppercase">
                    {o.group}
                  </p>
                )}
                <button
                  type="button"
                  role="option"
                  aria-selected={o.id === value}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => pick(o.id)}
                  className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm ${i === active ? 'bg-fill' : ''}`}
                >
                  <span className="min-w-0 flex-1">
                    <span
                      className={`${o.id ? 'text-ink' : 'text-ink-2'} ${mono && o.id ? 'font-mono' : ''}`}
                    >
                      {o.label}
                    </span>
                    {o.hint && <span className="block truncate text-xs text-ink-3">{o.hint}</span>}
                  </span>
                  {o.id === value && <Check className="size-3.5 text-ink" />}
                </button>
              </li>
            ))}
          </ul>
          {custom && (
            <div className="mt-1 border-t border-hairline px-1 pt-1.5">
              <input
                aria-label={custom.label}
                placeholder={custom.placeholder}
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') return
                  e.stopPropagation()
                  if (e.key !== 'Enter') return
                  e.preventDefault() // also keeps an enclosing form from submitting
                  if (typed.trim()) pick(typed.trim())
                  setTyped('')
                }}
                className="w-full rounded-md bg-transparent px-1.5 py-1 font-mono text-xs text-ink outline-none placeholder:text-ink-3 focus:bg-white/[0.04]"
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
