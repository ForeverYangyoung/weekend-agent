import type { DisplayPlan } from '../types'

interface Props {
  plan: DisplayPlan
  isTop1?: boolean
  onConfirm: (planId: string) => void
  onEditPreference: () => void
  disabled?: boolean
}

export function PlanCard({ plan, isTop1, onConfirm, onEditPreference, disabled }: Props) {
  const confirmDisabled = disabled || !plan.isValid

  return (
    <div className={`plan-card ${plan.isValid ? '' : 'plan-card-invalid'}`}>
      <div className="plan-card-header">
        <span className="plan-card-title">{plan.venueChain}</span>
        <span className="plan-card-subtitle">{plan.diffSummary}</span>
        {isTop1 && plan.isValid && <div className="badge-recommend">推荐</div>}
        {!plan.isValid && <div className="badge-invalid">需重规划</div>}
      </div>

      {!plan.isValid && (
        <div className="plan-constraint-issues">
          <div className="plan-issue-label">约束冲突，已禁止下单</div>
          {plan.constraintIssues.map((issue, i) => (
            <div key={i} className="plan-issue-item">{issue}</div>
          ))}
        </div>
      )}

      {plan.matchReasons.length > 0 && (
        <div className="plan-match-reasons">
          <div className="plan-match-label">约束命中（Profiler → Planner → Critic）</div>
          <div className="plan-match-tags">
            {plan.matchReasons.map((r, i) => (
              <span key={i} className="match-tag">{r}</span>
            ))}
          </div>
        </div>
      )}

      <div className="plan-timeline">
        {plan.timeline.map((item, index) => (
          <div key={`${item.kind}-${index}`}>
            {index > 0 && (
              <div className={`timeline-connector ${item.kind === 'addon' ? 'dashed' : ''}`} />
            )}
            <TimelineItem item={item} />
          </div>
        ))}
      </div>

      <div className="plan-card-footer">
        <span className="plan-price">{plan.totalPrice}</span>
      </div>

      <div className="plan-card-actions">
        <button
          type="button"
          className="btn-secondary"
          onClick={onEditPreference}
          disabled={disabled}
        >
          修改偏好重提
        </button>
        <button
          type="button"
          className="btn-primary"
          onClick={() => onConfirm(plan.id)}
          disabled={confirmDisabled}
        >
          {plan.isValid ? '选这个（一键下单）' : '先重新规划'}
        </button>
      </div>
    </div>
  )
}

function TimelineItem({
  item,
}: {
  item: DisplayPlan['timeline'][number]
}) {
  return (
    <div className={`timeline-item ${item.kind === 'addon' ? 'addon' : ''}`}>
      <div className="timeline-dot">
        <span className="timeline-kind">{item.label}</span>
      </div>
      <div className="timeline-content">
        <div className="timeline-time">{item.time}</div>
        <div className="timeline-name">{item.name}</div>
        <div className="timeline-desc">{item.desc}</div>
        {(item.priceLabel || item.distanceLabel) && (
          <div className="timeline-meta">
            {[item.priceLabel, item.distanceLabel].filter(Boolean).join(' · ')}
          </div>
        )}
        <div className="timeline-tags">
          {item.tags.map((t, i) => (
            <span key={i} className="tag">{t}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
