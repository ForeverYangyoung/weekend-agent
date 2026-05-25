import type { DisplayPlan } from '../types'

interface Props {
  plan: DisplayPlan
  onConfirm: (planId: string) => void
  disabled?: boolean
}

export function PlanCard({ plan, onConfirm, disabled }: Props) {
  return (
    <div className="plan-card">
      <div className="plan-card-header">
        <span className="plan-card-title">{plan.title}</span>
        <span className="plan-card-badge">推荐</span>
      </div>

      {/* Timeline stages */}
      <div className="plan-timeline">
        <TimelineItem
          icon="🎯"
          time={plan.play.time}
          name={plan.play.name}
          desc={plan.play.desc}
          tags={plan.play.tags}
        />
        <div className="timeline-connector" />
        <TimelineItem
          icon="🍽️"
          time={plan.eat.time}
          name={plan.eat.name}
          desc={plan.eat.desc}
          tags={plan.eat.tags}
        />
        {plan.addon && (
          <>
            <div className="timeline-connector dashed" />
            <TimelineItem
              icon="🧋"
              time="顺路"
              name={plan.addon.name}
              desc={plan.addon.desc}
              tags={plan.addon.tags}
              isAddon
            />
          </>
        )}
      </div>

      {/* Highlights */}
      <div className="plan-highlights">
        {plan.highlights.map((h, i) => (
          <span key={i} className="highlight-tag">{h}</span>
        ))}
      </div>

      {/* Footer */}
      <div className="plan-card-footer">
        <span className="plan-price">{plan.totalPrice}</span>
        <button
          className="confirm-btn"
          onClick={() => onConfirm(plan.id)}
          disabled={disabled}
        >
          选这个
        </button>
      </div>
    </div>
  )
}

function TimelineItem({
  icon, time, name, desc, tags, isAddon,
}: {
  icon: string
  time: string
  name: string
  desc: string
  tags: string[]
  isAddon?: boolean
}) {
  return (
    <div className={`timeline-item ${isAddon ? 'addon' : ''}`}>
      <div className="timeline-dot">
        <span className="timeline-emoji">{icon}</span>
      </div>
      <div className="timeline-content">
        <div className="timeline-time">{time}</div>
        <div className="timeline-name">{name}</div>
        <div className="timeline-desc">{desc}</div>
        <div className="timeline-tags">
          {tags.map((t, i) => (
            <span key={i} className="tag">{t}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
