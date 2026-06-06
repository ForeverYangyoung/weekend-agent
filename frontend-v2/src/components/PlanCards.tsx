import type { DisplayPlan } from '../types'
import { PlanCard } from './PlanCard'

interface Props {
  plans: DisplayPlan[]
  acceptedAlternatives?: Set<string>
  onConfirm: (planId: string) => void
  onEditPreference: () => void
  onAcceptAlternative?: (planId: string) => void
  onReject: () => void
  disabled?: boolean
}

export function PlanCards({
  plans,
  acceptedAlternatives,
  onConfirm,
  onEditPreference,
  onAcceptAlternative,
  onReject,
  disabled,
}: Props) {
  return (
    <div className="plan-cards">
      <div className="plan-cards-scroll">
        {plans.map((plan, index) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            isTop1={index === 0}
            alternativeAccepted={acceptedAlternatives?.has(plan.id)}
            onConfirm={onConfirm}
            onEditPreference={onEditPreference}
            onAcceptAlternative={onAcceptAlternative}
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
