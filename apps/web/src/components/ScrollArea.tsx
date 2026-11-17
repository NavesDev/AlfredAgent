import { useEffect, useRef, useState, type ReactNode, type Ref } from 'react'

/** Shortest the thumb gets, in pixels. */
const MIN_THUMB = 36
/** How long the bar stays after the last scroll, in ms. */
const LINGER = 900

type Props = {
  className?: string
  children: ReactNode
  ref?: Ref<HTMLDivElement>
}

/** A vertical scroll box with its own overlay bar: faint at rest, fades to full while scrolling
 * or under the pointer, widens under the pointer and can be dragged. The native bar is hidden because
 * WebKitGTK draws the GTK one (a light trough that pops in on hover). */
export function ScrollArea({ className = '', children, ref }: Props) {
  const box = useRef<HTMLDivElement | null>(null)
  const [thumb, setThumb] = useState({ top: 0, height: 0 })
  const [active, setActive] = useState(false)
  const [dragging, setDragging] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined)

  const setBox = (el: HTMLDivElement | null) => {
    box.current = el
    if (typeof ref === 'function') ref(el)
    else if (ref) ref.current = el
  }

  const measure = () => {
    const el = box.current
    if (!el) return
    const { clientHeight: view, scrollHeight: full, scrollTop } = el
    if (full <= view + 1) return setThumb({ top: 0, height: 0 })
    const height = Math.max(MIN_THUMB, (view / full) * view)
    const top = (scrollTop / (full - view)) * (view - height)
    setThumb({ top, height })
  }

  useEffect(() => {
    const el = box.current
    if (!el) return
    measure()
    const resize = new ResizeObserver(measure)
    const watch = () => {
      resize.disconnect()
      resize.observe(el)
      for (const child of el.children) resize.observe(child)
    }
    watch()
    const mutation = new MutationObserver(watch)
    mutation.observe(el, { childList: true })
    return () => {
      resize.disconnect()
      mutation.disconnect()
      clearTimeout(timer.current)
    }
  }, [])

  const onScroll = () => {
    measure()
    setActive(true)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setActive(false), LINGER)
  }

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = box.current
    if (!el) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    setDragging(true)
    const startY = e.clientY
    const startTop = el.scrollTop
    const ratio = (el.scrollHeight - el.clientHeight) / (el.clientHeight - thumb.height)
    const target = e.currentTarget
    const move = (ev: PointerEvent) => {
      el.scrollTop = startTop + (ev.clientY - startY) * ratio
    }
    const up = () => {
      setDragging(false)
      target.removeEventListener('pointermove', move)
      target.removeEventListener('pointerup', up)
      target.removeEventListener('pointercancel', up)
    }
    target.addEventListener('pointermove', move)
    target.addEventListener('pointerup', up)
    target.addEventListener('pointercancel', up)
  }

  const shown = thumb.height > 0
  return (
    <div className="group/scroll relative size-full">
      <div ref={setBox} onScroll={onScroll} className={`no-scrollbar size-full ${className}`}>
        {children}
      </div>
      {shown && (
        <div
          aria-hidden
          data-dragging={dragging || undefined}
          onPointerDown={onPointerDown}
          style={{ top: thumb.top, height: thumb.height }}
          className={`group/thumb absolute right-0 flex w-4 justify-end py-0.5 pr-1 transition-opacity duration-300 ease-out group-hover/scroll:opacity-100 data-dragging:opacity-100 ${active ? 'opacity-100' : 'opacity-50'}`}
        >
          <div className="h-full w-[5px] rounded-full bg-white/35 transition-[width,background-color] duration-200 ease-out group-hover/thumb:w-2 group-hover/thumb:bg-white/40 group-data-dragging/thumb:w-2 group-data-dragging/thumb:bg-white/45" />
        </div>
      )}
    </div>
  )
}
