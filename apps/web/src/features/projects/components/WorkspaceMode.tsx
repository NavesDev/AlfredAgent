import { Picker } from '../../../components/Picker'
import { modeOptions, type Mode } from '../lib/projects'

type Props = {
  name: string
  isDefault: boolean
  mode: Mode | null
  globalMode: Mode
  onDefault: () => void
  onMode: (mode: Mode | null) => void
}

/** A folder workspace's place in feature work: default badge and where features get built. */
export function WorkspaceMode({ name, isDefault, mode, globalMode, onDefault, onMode }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {isDefault ? (
        <span className="rounded-full bg-apple-green/20 px-2 py-0.5 text-[11px] text-[#8ee6a6]">
          padrão
        </span>
      ) : (
        <button
          type="button"
          onClick={onDefault}
          aria-label={`Tornar ${name} padrão`}
          className="rounded-full px-2 py-0.5 text-[11px] text-ink-3 opacity-60 ring-1 ring-white/10 transition group-hover:opacity-100 hover:text-ink"
        >
          tornar padrão
        </button>
      )}
      <div className="w-52">
        <Picker
          compact
          label={`Features em ${name}`}
          value={mode ?? ''}
          options={modeOptions(globalMode)}
          onChange={(id) => onMode(id ? (id as Mode) : null)}
        />
      </div>
    </div>
  )
}
