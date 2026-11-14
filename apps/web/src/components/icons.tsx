import type { SVGProps } from 'react'

// A handful of Lucide outlines, inlined so the panel needs no icon package.

type Props = SVGProps<SVGSVGElement>

const Icon = ({ children, ...props }: Props) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.75}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
    className="size-4 shrink-0"
    {...props}
  >
    {children}
  </svg>
)

export const ChevronDown = (p: Props) => (
  <Icon {...p}>
    <path d="m6 9 6 6 6-6" />
  </Icon>
)
export const ChevronLeft = (p: Props) => (
  <Icon {...p}>
    <path d="m15 18-6-6 6-6" />
  </Icon>
)
export const Check = (p: Props) => (
  <Icon {...p}>
    <path d="M20 6 9 17l-5-5" />
  </Icon>
)
export const Plus = (p: Props) => (
  <Icon {...p}>
    <path d="M5 12h14M12 5v14" />
  </Icon>
)
export const Trash = (p: Props) => (
  <Icon {...p}>
    <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
  </Icon>
)
export const Folder = (p: Props) => (
  <Icon {...p}>
    <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
  </Icon>
)
export const GitBranch = (p: Props) => (
  <Icon {...p}>
    <circle cx="6" cy="6" r="2" />
    <circle cx="6" cy="18" r="2" />
    <circle cx="18" cy="8" r="2" />
    <path d="M6 8v8M18 10a6 6 0 0 1-6 6H8" />
  </Icon>
)
export const Sparkle = (p: Props) => (
  <Icon {...p}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6" />
  </Icon>
)
export const Terminal = (p: Props) => (
  <Icon {...p}>
    <path d="m4 17 6-6-6-6M12 19h8" />
  </Icon>
)
export const Image = (p: Props) => (
  <Icon {...p}>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <circle cx="9" cy="9" r="2" />
    <path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21" />
  </Icon>
)
export const Plug = (p: Props) => (
  <Icon {...p}>
    <path d="M12 22v-5M9 8V2M15 8V2M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" />
  </Icon>
)
export const Gauge = (p: Props) => (
  <Icon {...p}>
    <path d="m12 14 4-4M3.34 19a10 10 0 1 1 17.32 0" />
  </Icon>
)
export const LayoutGrid = (p: Props) => (
  <Icon {...p}>
    <rect x="3" y="3" width="7" height="7" rx="1.5" />
    <rect x="14" y="3" width="7" height="7" rx="1.5" />
    <rect x="3" y="14" width="7" height="7" rx="1.5" />
    <rect x="14" y="14" width="7" height="7" rx="1.5" />
  </Icon>
)
export const Settings = (p: Props) => (
  <Icon {...p}>
    <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
    <circle cx="12" cy="12" r="3" />
  </Icon>
)
export const Mic = (p: Props) => (
  <Icon {...p}>
    <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM19 11a7 7 0 0 1-14 0M12 18v3" />
  </Icon>
)
export const Stop = (p: Props) => (
  <Icon {...p}>
    <rect x="7" y="7" width="10" height="10" rx="2" />
  </Icon>
)
export const Search = (p: Props) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-4-4" />
  </Icon>
)
export const X = (p: Props) => (
  <Icon {...p}>
    <path d="M18 6 6 18M6 6l12 12" />
  </Icon>
)
export const RotateCcw = (p: Props) => (
  <Icon {...p}>
    <path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5" />
  </Icon>
)
export const Transcript = (p: Props) => (
  <Icon {...p}>
    <path d="M4 6h16M4 12h16M4 18h10" />
  </Icon>
)
export const ChevronRight = (p: Props) => (
  <Icon {...p}>
    <path d="m9 18 6-6-6-6" />
  </Icon>
)
export const BarChart = (p: Props) => (
  <Icon {...p}>
    <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
  </Icon>
)
