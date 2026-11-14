import type { OrbMotion } from '../lib/orb'

const BANDS = [
  'h-[16%] bg-[linear-gradient(90deg,transparent_5%,#d95b56_25%,#ffa24c_42%,#fff4e0_52%,#93f1ff_62%,#3569fa_80%,transparent_95%)] blur-[9px]',
  'h-[9%] opacity-80 bg-[linear-gradient(90deg,transparent_10%,#3569fa_30%,#93f1ff_50%,#ffe0b3_66%,transparent_90%)] blur-[9px] [animation-direction:reverse]',
  'h-[4%] bg-[linear-gradient(90deg,transparent_15%,#ffa24c_40%,#fff_50%,#93f1ff_58%,transparent_85%)] blur-[3px]',
]

/** Glass ball with blurred spectral bands, the stand-in for Strands without WebGL2. */
export function CssOrb({ motion }: { motion: OrbMotion }) {
  const pace = 6 / Math.max(motion.speed, 0.1) / (motion.listening ? 3 : 1)
  const height = 0.6 + motion.energy * 0.6
  return (
    <div className="relative isolate size-full overflow-hidden rounded-full bg-[radial-gradient(circle_at_50%_120%,rgba(147,241,255,0.14),transparent_55%),radial-gradient(circle_at_50%_45%,#0b0d12_0%,#030305_75%)] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.22),inset_0_-18px_50px_rgba(255,255,255,0.08),0_30px_80px_rgba(0,0,0,0.5)]">
      {BANDS.map((band, i) => (
        <div
          key={i}
          style={{
            animationDuration: `${pace * (1 - i * 0.2)}s`,
            scale: `1 ${height}`,
            opacity: Math.min(1, 0.45 + motion.energy * 0.6),
          }}
          className={`animate-band absolute inset-x-[-10%] top-1/2 rounded-full mix-blend-screen ${band}`}
        />
      ))}
      <div className="absolute inset-0 rounded-full bg-[radial-gradient(ellipse_45%_22%_at_38%_14%,rgba(255,255,255,0.28),transparent_70%)]" />
    </div>
  )
}
