/** SSE event from the backend streaming endpoint */
export interface SSEEvent {
  event: 'start' | 'state' | 'final' | 'done' | 'error'
  user_input?: string
  force_failure?: string | null
  state?: AgentStatePayload
  summary?: SummaryPayload
  summary_card?: SummaryCard
  message?: string
}

export interface AgentStatePayload {
  user_input?: string
  trace?: string[]
  group_profile?: {
    scene?: string
    people_count?: number
    kids_ages?: number[]
    start_time?: string
    duration_h?: number
    distance_limit_km?: number
    dietary_tags?: string[]
    interests?: string[]
    budget?: string
    [key: string]: unknown
  }
  plans?: PlanPayload[]
  plan_iteration?: number
  executed_calls?: unknown[]
  failed_calls?: unknown[]
}

export interface PlanPayload {
  stage_order?: string[]
  play?: PlanStage
  eat?: PlanStage
  addon?: PlanStage
  total_budget?: number
  score?: number
}

export interface PlanStage {
  poi_name?: string
  poi_id?: string
  category?: string
  booking_ref?: string
  price?: number
  lat?: number
  lng?: number
  tags?: string[]
  duration_min?: number
}

export interface SummaryPayload {
  scene?: string
  plan_iteration?: number
  executed?: number
  failed?: number
}

export interface SummaryCard {
  title?: string
  share_text?: string
  body_markdown?: string
}

/** Frontend message model for the chat UI */
export interface ChatMessage {
  id: string
  role: 'ai' | 'user'
  type: 'text' | 'progress' | 'plans' | 'preferences' | 'welcome'
  text?: string
  plans?: DisplayPlan[]
  progressSteps?: ProgressStep[]
  preferences?: PreferenceState
  timestamp: number
}

export interface DisplayPlan {
  id: string
  title: string
  play: { name: string; time: string; desc: string; tags: string[] }
  eat: { name: string; time: string; desc: string; tags: string[] }
  addon?: { name: string; desc: string; tags: string[] }
  totalPrice: string
  score: number
  highlights: string[]
}

export interface ProgressStep {
  label: string
  done: boolean
}

export interface PreferenceState {
  foodTags: FoodTag[]
  activityTags: ActivityTag[]
  priorities: Priority[]
}

export interface FoodTag {
  id: string
  label: string
  emoji: string
  selected: boolean
  recommended: boolean
}

export interface ActivityTag {
  id: string
  label: string
  emoji: string
  selected: boolean
  recommended: boolean
}

export interface Priority {
  id: string
  label: string
  emoji: string
  order: number
}

/** App view states */
export type AppState =
  | 'idle'
  | 'streaming'
  | 'plans_displayed'
  | 'preferences'
  | 'confirmed'
