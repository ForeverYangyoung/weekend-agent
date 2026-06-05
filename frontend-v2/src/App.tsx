import { useState, useRef, useEffect, useCallback } from 'react'
import type {
  ChatMessage,
  DisplayPlan,
  ProfileChip,
  ProfileOverride,
  ProgressStep,
  SSEEvent,
} from './types'
import { confirmAgent, replanAgent, streamAgent } from './api'
import { mapPlansFromBackend } from './mapPlans'
import { InputBar } from './components/InputBar'
import { WelcomeScreen } from './components/WelcomeScreen'
import { ProgressIndicator } from './components/ProgressIndicator'
import { PlanCards } from './components/PlanCards'
import { PreferencePanel } from './components/PreferencePanel'
import { ProfileChips } from './components/ProfileChips'

const DEFAULT_PANEL_PREFS = {
  distance: '5公里内',
  diet: '重口味',
  vibe: '轻松社交',
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'welcome',
    role: 'ai',
    type: 'welcome',
    text:
      '嗨，我是你的周末小助手。支持家庭出游和朋友聚会两种场景：\n我会先预检可订资源，你确认后再一键下单。\n\n家庭场景：请带上人数及特殊要求（如：带5岁娃，需要健康餐）\n\n朋友场景：请告诉我人数和口味偏好（如：4个人，想吃重口味）',
    timestamp: Date.now(),
  },
]

const SUGGESTED_PROMPTS = [
  '我下午想和老婆孩子一起出去玩，老婆正在减肥，孩子5岁',
  '下午和三个朋友一起出去，4个人，别太远，想吃重口味',
]

const TRACE_PROGRESS: Array<{ prefix: string; label: string }> = [
  { prefix: '[Profiler]', label: '正在理解您的出行画像…' },
  { prefix: '[Researcher]', label: '正在搜索游玩与餐厅候选…' },
  { prefix: '[Planner]', label: '正在规划行程顺序…' },
  { prefix: '[TargetedResearcher]', label: '正在补充顺路小店…' },
  { prefix: '[Executor·预检]', label: '正在打听票位与库存…' },
]

function genId() {
  return Math.random().toString(36).slice(2, 10)
}

function progressFromTrace(trace: string[]): ProgressStep[] {
  return TRACE_PROGRESS.map(({ prefix, label }) => ({
    label,
    done: trace.some((line) => line.includes(prefix)),
  }))
}

function chipLabelForOverride(override: ProfileOverride): string {
  if (override.key === 'district') return override.value
  if (override.key === 'budget_per_person') return `约 ¥${override.value}/人`
  if (override.key === 'people_count') return `${override.value} 人`
  if (override.key === 'distance_limit_km') return `≤ ${override.value} km`
  return override.value
}

function sceneChipForPeople(count: number): ProfileChip | null {
  if (count >= 3) {
    return { key: 'scene', label: '朋友', value: 'friends', source: 'utterance', editable: true }
  }
  if (count === 2) {
    return { key: 'scene', label: '情侣', value: 'couple', source: 'utterance', editable: true }
  }
  if (count === 1) {
    return { key: 'scene', label: '独自', value: 'solo', source: 'utterance', editable: true }
  }
  return null
}

function mergeProfileChips(prev: ProfileChip[], override: ProfileOverride): ProfileChip[] {
  let next = prev.filter((c) => {
    if (override.key === 'people_count') {
      return (
        c.key !== 'people_count'
        && c.key !== 'scene'
        && !(c.key === 'interests' && /^\d+人?$/.test(c.value))
      )
    }
    if (override.key === 'dietary' && override.action === 'set') return c.key !== 'dietary'
    if (override.key === 'interests' && override.action === 'set') return c.key !== 'interests'
    if (override.action === 'add') {
      return !(c.key === override.key && c.value === override.value)
    }
    if (override.action === 'set') {
      return c.key !== override.key
    }
    return true
  })

  const chip: ProfileChip = {
    key: override.key,
    label: chipLabelForOverride(override),
    value: override.value,
    source: 'utterance',
    editable: true,
  }
  next = [...next, chip]

  if (override.key === 'people_count') {
    const n = Number.parseInt(override.value, 10)
    const sceneChip = sceneChipForPeople(n)
    if (sceneChip) next = [...next.filter((c) => c.key !== 'scene'), sceneChip]
  }

  return next
}

function panelToOverrides(prefs: typeof DEFAULT_PANEL_PREFS): ProfileOverride[] {
  const km = prefs.distance.match(/(\d+)/)?.[1] ?? '8'
  return [
    { key: 'distance_limit_km', value: km, action: 'set' },
    { key: 'dietary', value: prefs.diet, action: 'set' },
    { key: 'interests', value: prefs.vibe, action: 'set' },
  ]
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES)
  const [appState, setAppState] = useState<
    'idle' | 'streaming' | 'plans_displayed' | 'hil_editing' | 'confirmed'
  >('idle')
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([])
  const [plans, setPlans] = useState<DisplayPlan[]>([])
  const [profileChips, setProfileChips] = useState<ProfileChip[]>([])
  const [pendingOverrides, setPendingOverrides] = useState<ProfileOverride[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [inputDisabled, setInputDisabled] = useState(false)
  const [isReplanning, setIsReplanning] = useState(false)
  const [isPreferencePanelOpen, setIsPreferencePanelOpen] = useState(false)
  const [panelPreferences, setPanelPreferences] = useState(DEFAULT_PANEL_PREFS)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, progressSteps, appState, profileChips, scrollToBottom])

  function addMessage(msg: Omit<ChatMessage, 'id' | 'timestamp'>) {
    const full: ChatMessage = { ...msg, id: genId(), timestamp: Date.now() }
    setMessages((prev) => [...prev, full])
    return full
  }

  async function consumePlanningStream(events: AsyncGenerator<SSEEvent>) {
    let awaiting: SSEEvent | null = null
    let lastTrace: string[] = []

    for await (const ev of events) {
      if (ev.event === 'state' && ev.state?.trace) {
        lastTrace = ev.state.trace
        setProgressSteps(progressFromTrace(lastTrace))
      }
      if (ev.event === 'awaiting_confirm') {
        awaiting = ev
      }
      if (ev.event === 'error') {
        throw new Error(ev.message ?? '规划失败')
      }
    }

    if (!awaiting?.session_id || !awaiting.plans?.length) {
      throw new Error('未收到可确认的方案，请重试')
    }

    setSessionId(awaiting.session_id)
    setProfileChips(awaiting.profile_chips ?? [])
    setPendingOverrides([])
    setPlans(mapPlansFromBackend(awaiting.plans))
    setProgressSteps(progressFromTrace(lastTrace).map((s) => ({ ...s, done: true })))

    const chipText = (awaiting.profile_chips ?? []).map((c) => c.label).join('、')
    const planMsg = addMessage({
      role: 'ai',
      type: 'plans',
      text: chipText
        ? `已按约束（${chipText}）筛出 ${awaiting.plans.length} 套不同店组合。卡片绿标是各 Agent 的命中说明；备选会标明与推荐的差异。`
        : '预检完成！下方是真实候选方案。可点标签修改偏好后重搜，满意再点「选这个」确认下单。',
    })
    planMsg.plans = mapPlansFromBackend(awaiting.plans)

    setAppState('plans_displayed')
    setInputDisabled(false)
    setIsReplanning(false)
  }

  function handleSend(text: string) {
    if (!text.trim() || inputDisabled) return

    addMessage({ role: 'user', type: 'text', text: text.trim() })
    setAppState('streaming')
    setInputDisabled(true)
    setProgressSteps(TRACE_PROGRESS.map((t) => ({ label: t.label, done: false })))
    setPendingOverrides([])
    setSessionId(null)

    runInitialStream(text.trim())
  }

  async function runInitialStream(userInput: string) {
    try {
      await consumePlanningStream(streamAgent(userInput))
    } catch (err) {
      setProgressSteps([])
      setAppState('idle')
      setInputDisabled(false)
      addMessage({
        role: 'ai',
        type: 'text',
        text: `抱歉，规划过程中出现了问题：${err instanceof Error ? err.message : '未知错误'}。请重试一下。`,
      })
    }
  }

  function handleRemoveChip(override: ProfileOverride) {
    setPendingOverrides((prev) => [...prev, override])
    setProfileChips((prev) =>
      prev.filter((c) => !(c.key === override.key && c.value === override.value)),
    )
    setAppState('hil_editing')
  }

  function handleAddChip(override: ProfileOverride) {
    setPendingOverrides((prev) => [...prev, override])
    setProfileChips((prev) => mergeProfileChips(prev, override))
    setAppState('hil_editing')
  }

  async function runReplanStream(overrides: ProfileOverride[], userText: string) {
    if (!sessionId) return

    setAppState('streaming')
    setInputDisabled(true)
    setIsReplanning(true)
    setProgressSteps(TRACE_PROGRESS.map((t) => ({ label: t.label, done: false })))
    setPendingOverrides(overrides)

    addMessage({ role: 'user', type: 'text', text: userText })

    try {
      await consumePlanningStream(replanAgent(sessionId, overrides))
    } catch (err) {
      setProgressSteps([])
      setAppState('hil_editing')
      setInputDisabled(false)
      setIsReplanning(false)
      addMessage({
        role: 'ai',
        type: 'text',
        text: `重规划失败：${err instanceof Error ? err.message : '未知错误'}`,
      })
    }
  }

  async function handleReplan() {
    const text =
      pendingOverrides.length > 0
        ? `按新偏好重规划（${pendingOverrides.length} 项调整）`
        : '重新规划'
    await runReplanStream(pendingOverrides, text)
  }

  async function handleConfirmPlan(planId: string) {
    if (!sessionId) return
    const plan = plans.find((p) => p.id === planId)
    if (!plan) return

    setInputDisabled(true)
    addMessage({
      role: 'user',
      type: 'text',
      text: `确认选择：${plan.title}`,
    })

    try {
      const result = await confirmAgent(sessionId, planId)
      const orderLines = result.orders
        .map((o) => `✅ ${o.stage} 已下单 · 订单号 ${o.order_id}`)
        .join('\n')

      addMessage({
        role: 'ai',
        type: 'text',
        text: `好的！已为您确认「${plan.title}」并完成下单。\n\n${orderLines || '（无订单回执）'}\n\n${result.summary_card?.share_text ?? ''}`,
      })
      setAppState('confirmed')
    } catch (err) {
      setInputDisabled(false)
      addMessage({
        role: 'ai',
        type: 'text',
        text: `下单失败：${err instanceof Error ? err.message : '未知错误'}`,
      })
    }
  }

  async function handlePreferenceSubmit(prefs: typeof DEFAULT_PANEL_PREFS) {
    setIsPreferencePanelOpen(false)
    const overrides = panelToOverrides(prefs)

    if (!sessionId) {
      handleSend(
        `帮我安排周末出行。距离${prefs.distance}，想吃${prefs.diet}，氛围${prefs.vibe}。`,
      )
      return
    }

    setProfileChips((prev) =>
      overrides.reduce((chips, o) => mergeProfileChips(chips, o), prev),
    )
    await runReplanStream(overrides, `按面板调整偏好（${prefs.diet} · ${prefs.distance}）`)
  }

  function handleRejectPlan() {
    addMessage({
      role: 'user',
      type: 'text',
      text: '不喜欢这些方案',
    })
    addMessage({
      role: 'ai',
      type: 'text',
      text: '没问题，请点改下方偏好标签（× 删除 / 添加新偏好），然后点「按新偏好重新规划」。',
    })
    setAppState('hil_editing')
  }

  const showChipEditor = appState === 'hil_editing' || appState === 'plans_displayed'

  return (
    <div className="app-container">
      <div className="app-phone">
        <div className="status-bar">
          <span className="status-time">9:41</span>
          <div className="status-icons">
            <svg width="17" height="11" viewBox="0 0 17 11"><rect x="0" y="0" width="15" height="11" rx="2" fill="none" stroke="#222" strokeWidth="0.8"/><rect x="2" y="2" width="11" height="7" rx="1" fill="#222"/></svg>
          </div>
        </div>

        <div className="chat-header">
          <div className="header-avatar">W</div>
          <div>
            <div className="header-title">Weekend Agent</div>
            <div className="header-subtitle">周末出游助手 · HIL 在线</div>
          </div>
        </div>

        <div className="chat-messages">
          {messages.map((msg) => {
            if (msg.type === 'welcome') {
              return (
                <div key={msg.id} className="msg-row msg-ai">
                  <WelcomeScreen
                    greeting={msg.text ?? ''}
                    prompts={SUGGESTED_PROMPTS}
                    onPromptClick={handleSend}
                    disabled={inputDisabled}
                  />
                </div>
              )
            }

            if (msg.type === 'plans' && msg.plans) {
              return (
                <div key={msg.id} className="msg-row msg-ai msg-plan-row">
                  <div className="ai-bubble ai-bubble-plan">
                    <div className="bubble-text">{msg.text}</div>
                    <PlanCards
                      plans={msg.plans}
                      onConfirm={handleConfirmPlan}
                      onEditPreference={() => setIsPreferencePanelOpen(true)}
                      onReject={handleRejectPlan}
                      disabled={appState === 'confirmed' || inputDisabled}
                    />
                  </div>
                </div>
              )
            }

            if (msg.role === 'user') {
              return (
                <div key={msg.id} className="msg-row msg-user">
                  <div className="user-bubble">{msg.text}</div>
                </div>
              )
            }

            return (
              <div key={msg.id} className="msg-row msg-ai">
                <div className="ai-bubble">
                  <div className="bubble-text">{msg.text}</div>
                </div>
              </div>
            )
          })}

          {showChipEditor && profileChips.length > 0 && (
            <div className="msg-row msg-ai">
              <ProfileChips
                chips={profileChips}
                editing={appState === 'hil_editing' || appState === 'plans_displayed'}
                onRemove={handleRemoveChip}
                onAdd={handleAddChip}
                onReplan={handleReplan}
                replanning={isReplanning}
              />
            </div>
          )}

          {appState === 'streaming' && progressSteps.length > 0 && (
            <div className="msg-row msg-ai">
              <ProgressIndicator steps={progressSteps} live />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <InputBar
          onSend={handleSend}
          disabled={inputDisabled}
          placeholder={
            appState === 'confirmed'
              ? '已确认，祝您周末愉快！'
              : appState === 'hil_editing'
                ? '或在上方修改偏好后点「重新规划」'
                : '家庭或朋友出游，说说人数、时间、饮食偏好…'
          }
        />

        <PreferencePanel
          open={isPreferencePanelOpen}
          preferences={panelPreferences}
          onChange={setPanelPreferences}
          onClose={() => setIsPreferencePanelOpen(false)}
          onSubmit={handlePreferenceSubmit}
        />
      </div>
    </div>
  )
}
