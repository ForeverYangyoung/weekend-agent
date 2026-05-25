import type { DisplayPlan } from '../types'
import { PlanCard } from './PlanCard'

interface Props {
  plans: DisplayPlan[]
  onConfirm: (planId: string) => void
  onReject: () => void
  disabled?: boolean
}

export function PlanCards({ plans, onConfirm, onReject, disabled }: Props) {
  return (
    <div className="plan-cards">
      <div className="plan-cards-scroll">
        {plans.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            onConfirm={onConfirm}
            disabled={disabled}
          />
        ))}
      </div>
      <button
        className="reject-btn"
        onClick={onReject}
        disabled={disabled}
      >
        都不喜欢，补充偏好重新规划
      </button>
    </div>
  )
}
