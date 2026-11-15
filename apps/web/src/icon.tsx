// The app icon page (icon.html): Alfred's orb at rest, drawn once for render_icon.mjs.
import { createRoot } from 'react-dom/client'
import Strands from './features/assistant/components/strands/Strands'
import { orbMotion } from './features/assistant/lib/orb'

declare global {
  interface Window {
    iconReady?: boolean
  }
}

const FRAMES_BEFORE_READY = 30

createRoot(document.getElementById('icon')!).render(
  <Strands
    {...orbMotion('idle', null)}
    interactive={false}
    intro={false}
    maxDevicePixelRatio={1}
  />,
)

let frames = 0
const wait = () =>
  ++frames < FRAMES_BEFORE_READY ? requestAnimationFrame(wait) : (window.iconReady = true)
requestAnimationFrame(wait)
