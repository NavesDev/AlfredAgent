// Release notes come as CHANGELOG markdown; the panel only needs headings, items and text.

export type NoteBlock = { kind: 'heading' | 'item' | 'text'; text: string }

/** Drops commit links, bold and code marks: "**web:** `x` ([abc](url))" → "web: x". */
const plain = (text: string) =>
  text
    .replace(/\s*\(\[[^\]]*\]\([^)]*\)\)/g, '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\*\*|`/g, '')
    .trim()

export function noteBlocks(notes: string): NoteBlock[] {
  return notes
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line): NoteBlock => {
      if (line.startsWith('#')) return { kind: 'heading', text: plain(line.replace(/^#+/, '')) }
      if (/^[*-] /.test(line)) return { kind: 'item', text: plain(line.slice(2)) }
      return { kind: 'text', text: plain(line) }
    })
}
