/** Alfred's mark on a result: a still, tiny version of the orb's spectral band. */
export function MiniOrb({ className = 'size-[18px]' }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={`shrink-0 rounded-full bg-[radial-gradient(circle_at_50%_58%,#fff_0_6%,#f2a35a_14%,#d95b56_24%,#3569fa_34%,#1c1c20_46%)] ${className}`}
    />
  )
}
