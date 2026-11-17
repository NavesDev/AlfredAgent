import { invoke, isTauri } from '@tauri-apps/api/core'
import { getCurrentWindow, Window } from '@tauri-apps/api/window'
import type { OverlayPosition } from '../api/events'
import type { Anchor } from './overlay'

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

/** Tells the shell which part of the overlay takes the mouse (the card); null lets every click
 * through. Logical pixels inside the window. */
export const setHitRect = (rect: [number, number, number, number] | null): Promise<void> =>
  invoke('set_hit_rect', { rect })

/** Where the overlay window is anchored. */
export const overlayAnchor = (): Promise<Anchor & { preset: OverlayPosition }> =>
  invoke('overlay_anchor')

/** Moves everything that floats to another preset (the shell rebuilds the overlay there). */
export const setOverlayPosition = (preset: OverlayPosition): Promise<void> =>
  invoke('set_overlay_position', { preset })

/** Opens (or points) the expanded result window at a result's slide. */
export const openViewer = (resultId: number, index: number): Promise<void> =>
  invoke('open_viewer', { resultId, index })
