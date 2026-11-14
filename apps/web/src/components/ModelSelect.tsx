import { MODELS } from '../lib/sessionForm'
import { Picker } from './Picker'

// Model picker: grouped list with a hint per model, plus a free field for any other id
// `claude --model` accepts.

type Props = {
  value: string
  onChange: (model: string) => void
  /** Shown for the empty value; without it the empty value is not offered. */
  placeholder?: string
  label: string
  compact?: boolean
}

export function ModelSelect({ value, onChange, placeholder, label, compact }: Props) {
  return (
    <Picker
      value={value}
      onChange={onChange}
      label={label}
      placeholder={placeholder}
      compact={compact}
      options={[...(placeholder ? [{ id: '', label: placeholder }] : []), ...MODELS]}
      custom={{ label: 'Outro modelo', placeholder: 'outro id (Enter)' }}
    />
  )
}
