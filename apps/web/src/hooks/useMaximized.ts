import { useEffect, useState } from 'react'
import { appWindow, isDesktop } from '../lib/desktop'

/** Whether the desktop window is maximized; mirrors it on <html> so the corners square off. */
export function useMaximized(): boolean {
  const [maximized, setMaximized] = useState(false)
  useEffect(() => {
    if (!isDesktop()) return
    const win = appWindow()
    const sync = () =>
      win.isMaximized().then((value) => {
        setMaximized(value)
        document.documentElement.classList.toggle('maximized', value)
      })
    void sync()
    const unlisten = win.onResized(sync)
    return () => void unlisten.then((stop) => stop())
  }, [])
  return maximized
}
