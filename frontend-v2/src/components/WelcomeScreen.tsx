interface Props {
  greeting: string
  prompts: string[]
  onPromptClick: (text: string) => void
  disabled: boolean
}

export function WelcomeScreen({ greeting, prompts, onPromptClick, disabled }: Props) {
  return (
    <div className="ai-bubble welcome-bubble">
      <div className="bubble-text welcome-text">{greeting}</div>
      <div className="welcome-hint">点下方示例可一键填入；不满意方案可点「修改偏好重提」。</div>
      <div className="welcome-prompts">
        {prompts.map((p, i) => (
          <button
            key={i}
            className="prompt-chip"
            onClick={() => onPromptClick(p)}
            disabled={disabled}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}
