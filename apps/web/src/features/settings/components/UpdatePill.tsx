import { Link } from 'react-router'
import { Download } from '../../../components/icons'
import { useUpdate } from '../hooks/useUpdate'

/** On the control bar only while a new release waits or is being installed. */
export function UpdatePill() {
  const { update } = useUpdate()
  if (!update?.available) return null
  const updating = update.status === 'updating'
  return (
    <Link
      to="/settings#atualizacoes"
      title={`Nova versão ${update.latest} disponível`}
      className="flex items-center gap-1.5 rounded-full bg-apple-blue/20 py-2 pr-3.5 pl-3 text-[12px] font-medium whitespace-nowrap text-[#64b5ff] transition-colors hover:bg-apple-blue/30"
    >
      <Download className="size-3.5" />
      {updating ? 'Atualizando…' : update.latest}
    </Link>
  )
}
