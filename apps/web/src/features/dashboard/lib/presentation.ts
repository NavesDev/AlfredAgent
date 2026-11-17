import type { PresentMode } from '../../../api/events'

/** The panel shows the result card in its corner (D15); on the desktop the expanded mode opens
 * the `viewer` window instead, a browser has none and gets the card. */
export const panelShowsCard = (mode: PresentMode | null, desktop: boolean): boolean =>
  mode === 'card' || (mode === 'ampliado' && !desktop)
