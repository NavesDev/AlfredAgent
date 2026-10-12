/** Monogram tile; the hue comes from the name so each project keeps its color. */
export function ProjectMark({ name, size = 'md' }: { name: string; size?: 'md' | 'lg' }) {
  const hue = [...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7)
  return (
    <span
      aria-hidden
      style={{
        background: `linear-gradient(135deg, hsl(${hue} 70% 55% / 0.28), hsl(${(hue + 40) % 360} 70% 40% / 0.12))`,
        borderColor: `hsl(${hue} 70% 65% / 0.3)`,
        color: `hsl(${hue} 80% 82%)`,
      }}
      className={`grid shrink-0 place-items-center rounded-xl border font-semibold ${size === 'lg' ? 'size-12 text-lg' : 'size-10 text-sm'}`}
    >
      {name.slice(0, 2).toUpperCase()}
    </span>
  )
}
