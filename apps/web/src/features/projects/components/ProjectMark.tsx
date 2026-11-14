const SIZE = { sm: 'size-8 text-sm', md: 'size-11 text-lg', lg: 'size-16 text-[28px]' }

/** App-icon tile with the project's initial; the hue comes from the name so it never changes. */
export function ProjectMark({ name, size = 'md' }: { name: string; size?: keyof typeof SIZE }) {
  const hue = [...name.toLowerCase()].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7)
  return (
    <span
      aria-hidden
      style={{
        background: `linear-gradient(160deg, hsl(${hue} 85% 62%), hsl(${(hue + 28) % 360} 80% 48%))`,
      }}
      className={`grid shrink-0 place-items-center rounded-[28%] font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.35)] ${SIZE[size]}`}
    >
      {name.trim()[0]?.toUpperCase()}
    </span>
  )
}
