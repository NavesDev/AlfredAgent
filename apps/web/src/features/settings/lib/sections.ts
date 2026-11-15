export type SectionId = 'uso' | 'modelos' | 'sessoes' | 'mcps' | 'atualizacoes'

/** The settings sidebar, in order; the id is the link anchor (/settings#mcps). */
export const SECTIONS: { id: SectionId; label: string; color: string }[] = [
  { id: 'uso', label: 'Uso e limites', color: 'bg-apple-blue' },
  { id: 'modelos', label: 'Modelos', color: 'bg-apple-purple' },
  { id: 'sessoes', label: 'Sessões abertas', color: 'bg-apple-orange' },
  { id: 'mcps', label: 'MCPs', color: 'bg-apple-green' },
  { id: 'atualizacoes', label: 'Atualizações', color: 'bg-[#636366]' },
]

export function sectionFromHash(hash: string): SectionId {
  const id = hash.replace(/^#/, '')
  return SECTIONS.find((s) => s.id === id)?.id ?? 'uso'
}
