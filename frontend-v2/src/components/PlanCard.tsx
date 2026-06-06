import type { DisplayPlan } from '../types'

interface Props {
  plan: DisplayPlan
  isTop1?: boolean
  alternativeAccepted?: boolean
  onConfirm: (planId: string) => void
  onEditPreference: () => void
  onAcceptAlternative?: (planId: string) => void
  disabled?: boolean
}

export function PlanCard({
  plan,
  isTop1,
  alternativeAccepted,
  onConfirm,
  onEditPreference,
  onAcceptAlternative,
  disabled,
}: Props) {
  const canOrder =
    plan.isValid || (plan.issueKind === 'alternative_available' && alternativeAccepted)
  const confirmDisabled = disabled || !canOrder
  const showIssuePanel = plan.planIssues.length > 0 && !canOrder

  const badgeLabel =
    plan.issueKind === 'needs_preference_fix'
      ? '待改偏好'
      : plan.issueKind === 'alternative_available'
        ? '就近替代'
        : '需重规划'

  const issuePanelClass =
    plan.issueKind === 'needs_preference_fix'
      ? 'plan-issue-panel plan-issue-panel-warn'
      : plan.issueKind === 'alternative_available'
        ? 'plan-issue-panel plan-issue-panel-info'
        : 'plan-issue-panel plan-issue-panel-error'

  return (
    <div className={`plan-card ${canOrder ? '' : 'plan-card-invalid'}`}>
      <div className="plan-card-header">
        <span className="plan-card-title">{plan.venueChain}</span>
        <span className="plan-card-subtitle">{plan.diffSummary}</span>
        {isTop1 && canOrder && <div className="badge-recommend">推荐</div>}
        {!canOrder && <div className="badge-invalid">{badgeLabel}</div>}
      </div>

      {plan.activeConstraints.length > 0 && (
        <div className="plan-active-constraints">
          <div className="plan-active-constraints-label">当前生效约束</div>
          <div className="plan-active-constraints-tags">
            {plan.activeConstraints.map((c, i) => (
              <span key={`${c}-${i}`} className="active-constraint-tag">{c}</span>
            ))}
          </div>
        </div>
      )}

      {showIssuePanel && (
        <div className={issuePanelClass}>
          {plan.planIssues.map((issue, i) => (
            <div key={i} className="plan-issue-block">
              <div className="plan-issue-label">{issue.headline}</div>
              <div className="plan-issue-item">{issue.detail}</div>
              {issue.suggestions && issue.suggestions.length > 0 && (
                <ul className="plan-issue-suggestions">
                  {issue.suggestions.map((s, j) => (
                    <li key={j}>{s}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      {plan.issueKind === 'alternative_available' && alternativeAccepted && (
        <div className="plan-issue-panel plan-issue-panel-accepted">
          <div className="plan-issue-label">已接受就近替代方案，可以下单</div>
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
        {plan.issueKind === 'alternative_available' && !alternativeAccepted && (
          <button
            type="button"
            className="btn-primary"
            onClick={() => onAcceptAlternative?.(plan.id)}
            disabled={disabled}
          >
            接受替代方案
          </button>
        )}
        <button
          type="button"
          className={
            plan.issueKind === 'needs_preference_fix' ? 'btn-primary' : 'btn-secondary'
          }
          onClick={onEditPreference}
          disabled={disabled}
        >
          {plan.issueKind === 'needs_preference_fix' ? '修改矛盾偏好' : '修改偏好重提'}
        </button>
        <button
          type="button"
          className={
            plan.issueKind === 'alternative_available' && !alternativeAccepted
              ? 'btn-secondary'
              : 'btn-primary'
          }
          onClick={() => onConfirm(plan.id)}
          disabled={confirmDisabled}
        >
          {canOrder
            ? '选这个（一键下单）'
            : plan.issueKind === 'needs_preference_fix'
              ? '请先改偏好'
              : plan.issueKind === 'alternative_available'
                ? '或先接受替代'
                : '先重新规划'}
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
