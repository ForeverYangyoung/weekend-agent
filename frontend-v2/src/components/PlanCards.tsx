import type { DisplayPlan } from '../types'
import { PlanCard } from './PlanCard'

interface Props {
  plans: DisplayPlan[]
  onConfirm: (planId: string) => void
  onEditPreference: () => void
  onReject: () => void
  disabled?: boolean
}

export function PlanCards({ plans, onConfirm, onEditPreference, onReject, disabled }: Props) {
  return (
    <div className="plan-cards">
      <div className="plan-cards-scroll">
        {plans.map((plan, index) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            isTop1={index === 0}
            onConfirm={onConfirm}
            onEditPreference={onEditPreference}
            disabled={disabled}
          />
        ))}
      </div>
      <button
        type="button"
        className="reject-btn"
        onClick={onReject}
        disabled={disabled}
      >
        都不喜欢，补充偏好重新规划
      </button>
    </div>
  )
}
