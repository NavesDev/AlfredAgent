// Renders the app icon from the real orb (ADR 0014): opens apps/web/icon.html, served by
// `make dev-web`, in headless Chromium with reduced motion (one fixed frame) and saves it as a
// transparent 1024px PNG. `pnpm icon` then makes every size with `tauri icon`.
import { chromium } from 'playwright'

const [out = 'assets/icon.png', url = 'http://localhost:5173/icon.html'] = process.argv.slice(2)
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
try {
  const page = await browser.newPage({ viewport: { width: 1024, height: 1024 }, reducedMotion: 'reduce' })
  await page.goto(url)
  await page.waitForFunction(() => window.iconReady === true, null, { timeout: 30_000 })
  await page.locator('#icon').screenshot({ path: out, omitBackground: true })
} finally {
  await browser.close()
}
