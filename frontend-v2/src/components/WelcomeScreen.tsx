import type { ScenarioId } from '../scenarioPresets'

interface Props {
  greeting: string
  onScenarioSelect: (id: ScenarioId) => void
  disabled: boolean
}

export function WelcomeScreen({ greeting, onScenarioSelect, disabled }: Props) {
  return (
    <div className="ai-bubble welcome-bubble">
      <div className="bubble-text welcome-text">{greeting}</div>
      <div className="welcome-hint">
        先选场景，再补充偏好（如家庭场景也可加「火锅」），确认后一键规划。
      </div>
      <div className="scenario-cards">
        <button
          type="button"
          className="scenario-card scenario-card-family"
          onClick={() => onScenarioSelect('family')}
          disabled={disabled}
        >
          <div className="scenario-card-title">家庭场景</div>
          <div className="scenario-card-desc">3 人 · 5 岁娃 · 亲子活动</div>
          <div className="scenario-card-tip">可再加：火锅 / 轻食 / 日料</div>
        </button>
        <button
          type="button"
          className="scenario-card scenario-card-friends"
          onClick={() => onScenarioSelect('friends')}
          disabled={disabled}
        >
          <div className="scenario-card-title">朋友场景</div>
          <div className="scenario-card-desc">4 人 · 重口味 · 社交聚餐</div>
          <div className="scenario-card-tip">演示满座回滚与重规划</div>
        </button>
      </div>
    </div>
  )
}
