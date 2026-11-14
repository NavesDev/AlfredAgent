import type { ReactNode } from 'react'
import { useConnection } from '../../hooks/useEvents'
import { NavRail } from './NavRail'

/** Out-of-focus graphite shapes, so the glass panels have something to blur. */
function Room() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-[linear-gradient(180deg,#19191c_0%,#0f0f11_55%,#09090b_100%)]" />
      <div className="absolute top-[8%] -left-[6%] h-[55%] w-[40%] rounded-full bg-[#3c3c42] opacity-60 blur-[60px]" />
      <div className="absolute -top-[6%] right-[6%] h-[40%] w-[26%] rounded-full bg-[#8a8a94] opacity-[0.22] blur-[60px]" />
      <div className="absolute -bottom-[10%] left-[30%] h-[30%] w-[50%] rounded-full bg-[#2a2a30] opacity-60 blur-[60px]" />
      <div className="absolute top-0 left-[46%] h-[70%] w-[18%] rounded-full bg-[#303036] opacity-50 blur-[60px]" />
    </div>
  )
}

/** Every page: the room, the nav rail on the left (top on phones) and the page's panels. */
export function AppShell({ children }: { children: ReactNode }) {
  const connection = useConnection()
  return (
    <div className="relative h-full overflow-hidden text-ink">
      <Room />
      <div className="relative flex h-full flex-col gap-4 p-4 md:flex-row md:items-stretch md:gap-6 md:p-8">
        <div className="flex shrink-0 justify-center md:items-center">
          <NavRail connection={connection} />
        </div>
        <div className="min-h-0 min-w-0 flex-1">{children}</div>
      </div>
    </div>
  )
}
