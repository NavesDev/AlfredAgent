import { invoke, isTauri } from '@tauri-apps/api/core'
import { getCurrentWindow, Window } from '@tauri-apps/api/window'

/** Running inside the Tauri app (apps/desktop) instead of a browser tab. */
export const isDesktop = (): boolean => isTauri()

/** The window this page lives in; only call it when `isDesktop()`. */
export const appWindow = () => getCurrentWindow()

/** The panel window is out of sight: minimized, or hidden in the tray. */
export async function panelOutOfSight(): Promise<boolean> {
  const panel = await Window.getByLabel('main')
  if (!panel) return true
  const [visible, minimized] = await Promise.all([panel.isVisible(), panel.isMinimized()])
  return !visible || minimized
}

/** Tells the shell the voice pill is on screen, so it lets the mouse grab it (to drag). */
export const setPillShown = (shown: boolean): Promise<void> => invoke('set_pill_shown', { shown })
