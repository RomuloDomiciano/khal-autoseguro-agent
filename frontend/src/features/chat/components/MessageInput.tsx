import { useState, type FormEvent } from 'react'

interface MessageInputProps {
  disabled: boolean
  disabledReason?: string
  onSend: (text: string) => void
}

export function MessageInput({ disabled, disabledReason, onSend }: MessageInputProps) {
  const [value, setValue] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (disabled || !value.trim()) return
    onSend(value)
    setValue('')
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <label htmlFor="chat-message" className="chat-visually-hidden">
        Mensagem
      </label>
      <input
        id="chat-message"
        className="chat-input__field"
        type="text"
        autoComplete="off"
        placeholder={disabled ? disabledReason ?? 'Aguarde...' : 'Digite sua mensagem...'}
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
      />
      <button type="submit" className="chat-input__send" disabled={disabled || !value.trim()}>
        Enviar
      </button>
    </form>
  )
}
