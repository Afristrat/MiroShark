<template>
  <!--
    ReportChatPanel (US-111) — Sliding panel that lets the user chat with
    the report agent (POST /api/report/chat). History is persisted in
    localStorage under bassira:report:<reportId>:chat.

    Layout: 380px wide, fixed to inset-inline-end (RTL-friendly), full
    height, slides in from the side. Tokens --wi-* exclusively. i18n
    FR/EN/AR via $t('report.chat.*').
  -->
  <transition name="rcp-slide">
    <aside
      v-if="open"
      class="rcp-panel"
      :aria-label="$t('report.chat.title')"
      role="complementary"
    >
      <header class="rcp-header">
        <div class="rcp-header-text">
          <span class="rcp-eyebrow">{{ $t('report.chat.title') }}</span>
          <span class="rcp-subtitle">{{ $t('report.chat.subtitle') }}</span>
        </div>
        <div class="rcp-header-actions">
          <button
            v-if="messages.length > 0"
            type="button"
            class="rcp-icon-btn"
            :title="$t('report.chat.clear')"
            :aria-label="$t('report.chat.clear')"
            @click="clearHistory"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6m5 0V4a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
          <button
            type="button"
            class="rcp-icon-btn"
            :title="$t('report.actions.closeChat')"
            :aria-label="$t('report.actions.closeChat')"
            @click="$emit('close')"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </header>

      <div ref="scrollEl" class="rcp-messages">
        <div v-if="messages.length === 0 && !isSending" class="rcp-empty">
          <span>{{ $t('report.chat.empty') }}</span>
        </div>

        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="rcp-message"
          :class="`is-${msg.role}`"
        >
          <span class="rcp-message-role">
            {{ msg.role === 'user' ? $t('report.chat.you') : $t('report.chat.assistant') }}
          </span>
          <div class="rcp-message-bubble" v-html="renderMd(msg.content)"></div>
        </div>

        <div v-if="isSending" class="rcp-message is-assistant">
          <span class="rcp-message-role">{{ $t('report.chat.assistant') }}</span>
          <div class="rcp-message-bubble is-thinking">
            <span class="rcp-thinking-dot"></span>
            <span class="rcp-thinking-dot"></span>
            <span class="rcp-thinking-dot"></span>
            <span class="rcp-thinking-text">{{ $t('report.chat.thinking') }}</span>
          </div>
        </div>

        <div v-if="errorMsg" class="rcp-error" role="alert">
          {{ errorMsg }}
        </div>
      </div>

      <form class="rcp-input-row" @submit.prevent="onSubmit">
        <textarea
          v-model="draft"
          class="rcp-textarea"
          rows="2"
          :placeholder="$t('report.chat.placeholder')"
          :disabled="isSending || !simulationId"
          @keydown.enter.exact.prevent="onSubmit"
        ></textarea>
        <button
          type="submit"
          class="rcp-send-btn"
          :disabled="isSending || !draft.trim() || !simulationId"
        >
          <span v-if="!isSending">{{ $t('report.chat.send') }}</span>
          <span v-else>{{ $t('report.chat.sending') }}</span>
          <svg v-if="!isSending" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </form>
    </aside>
  </transition>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { chatWithReport } from '../api/report'
import { renderMarkdown } from '../utils/markdown'

const props = defineProps({
  open: { type: Boolean, default: false },
  reportId: { type: String, default: '' },
  simulationId: { type: String, default: '' }
})

defineEmits(['close'])

const { t } = useI18n()

const messages = ref([])
const draft = ref('')
const isSending = ref(false)
const errorMsg = ref('')
const scrollEl = ref(null)

const storageKey = () => (props.reportId ? `bassira:report:${props.reportId}:chat` : null)

const loadHistory = () => {
  const key = storageKey()
  if (!key) {
    messages.value = []
    return
  }
  try {
    const raw = localStorage.getItem(key)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        messages.value = parsed.filter(
          (m) => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string'
        )
        return
      }
    }
  } catch (_) {
    // Corrupt or unreadable storage — start fresh.
  }
  messages.value = []
}

const persistHistory = () => {
  const key = storageKey()
  if (!key) return
  try {
    localStorage.setItem(key, JSON.stringify(messages.value.slice(-40)))
  } catch (_) {
    // Quota exceeded or storage unavailable — silently drop.
  }
}

const renderMd = (content) => {
  try {
    return renderMarkdown(content || '')
  } catch (_) {
    return (content || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollEl.value) {
      scrollEl.value.scrollTop = scrollEl.value.scrollHeight
    }
  })
}

const clearHistory = () => {
  messages.value = []
  errorMsg.value = ''
  const key = storageKey()
  if (key) {
    try {
      localStorage.removeItem(key)
    } catch (_) {
      /* noop */
    }
  }
}

const onSubmit = async () => {
  const text = draft.value.trim()
  if (!text || isSending.value || !props.simulationId) return

  errorMsg.value = ''
  messages.value.push({ role: 'user', content: text })
  draft.value = ''
  persistHistory()
  scrollToBottom()

  isSending.value = true
  try {
    const history = messages.value
      .slice(0, -1) // Don't include the message we just added (backend treats it as the new query)
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content }))

    const res = await chatWithReport({
      simulation_id: props.simulationId,
      message: text,
      chat_history: history
    })

    if (res?.success && res.data) {
      const reply = res.data.response || ''
      messages.value.push({ role: 'assistant', content: reply })
      persistHistory()
      scrollToBottom()
    } else {
      errorMsg.value = res?.error || t('report.chat.error')
    }
  } catch (err) {
    errorMsg.value = err?.response?.data?.error || err?.message || t('report.chat.error')
  } finally {
    isSending.value = false
    scrollToBottom()
  }
}

watch(
  () => props.open,
  (val) => {
    if (val) {
      loadHistory()
      scrollToBottom()
    }
  }
)

watch(
  () => props.reportId,
  () => {
    if (props.open) loadHistory()
  }
)

onMounted(() => {
  if (props.open) loadHistory()
})
</script>

<style scoped>
.rcp-panel {
  position: fixed;
  top: 0;
  inset-inline-end: 0;
  bottom: 0;
  width: 380px;
  max-width: 92vw;
  background: var(--wi-surface);
  border-inline-start: 1px solid var(--wi-outline-variant);
  box-shadow: var(--wi-shadow-lg);
  z-index: var(--ms-z-modal, 100);
  display: flex;
  flex-direction: column;
  font-family: var(--wi-font-body);
  color: var(--wi-on-surface);
}

.rcp-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-md);
  background: var(--wi-on-bg);
  color: var(--wi-bg);
  border-bottom: 1px solid var(--wi-outline-variant);
}

.rcp-header-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.rcp-eyebrow {
  font-family: var(--wi-font-body);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--wi-bg);
}

.rcp-subtitle {
  font-size: 11px;
  font-weight: 400;
  color: var(--wi-bg);
  opacity: 0.75;
  line-height: 1.4;
}

.rcp-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.rcp-icon-btn {
  appearance: none;
  background: rgba(250, 247, 242, 0.08);
  border: 1px solid rgba(250, 247, 242, 0.2);
  color: var(--wi-bg);
  width: 28px;
  height: 28px;
  border-radius: var(--wi-radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background var(--ms-transition);
}

.rcp-icon-btn:hover {
  background: rgba(250, 247, 242, 0.15);
}

.rcp-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  background: var(--wi-bg);
}

.rcp-empty {
  margin: auto;
  text-align: center;
  color: var(--wi-on-surface-variant);
  font-size: 13px;
  padding: var(--wi-space-lg);
}

.rcp-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rcp-message-role {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--wi-outline);
}

.rcp-message.is-user {
  align-self: flex-end;
  max-width: 85%;
}

.rcp-message.is-assistant {
  align-self: flex-start;
  max-width: 95%;
}

.rcp-message-bubble {
  padding: 10px 12px;
  border-radius: var(--wi-radius-card);
  font-size: 13px;
  line-height: 1.55;
  word-wrap: break-word;
  overflow-wrap: anywhere;
}

.rcp-message.is-user .rcp-message-bubble {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  border-end-end-radius: var(--wi-radius-sm);
}

.rcp-message.is-assistant .rcp-message-bubble {
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  border: 1px solid var(--wi-outline-variant);
  border-end-start-radius: var(--wi-radius-sm);
}

.rcp-message-bubble :deep(p) {
  margin: 0 0 8px;
}
.rcp-message-bubble :deep(p:last-child) {
  margin-bottom: 0;
}
.rcp-message-bubble :deep(ul),
.rcp-message-bubble :deep(ol) {
  margin: 4px 0 8px;
  padding-inline-start: 18px;
}
.rcp-message-bubble :deep(code) {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  background: var(--wi-outline-variant);
  padding: 1px 4px;
  border-radius: 3px;
}
.rcp-message-bubble :deep(pre) {
  background: var(--wi-on-bg);
  color: var(--wi-bg);
  padding: 8px;
  border-radius: var(--wi-radius-sm);
  overflow-x: auto;
}

.rcp-message-bubble.is-thinking {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--wi-on-surface-variant);
}

.rcp-thinking-dot {
  width: 5px;
  height: 5px;
  background: var(--wi-on-primary-container);
  border-radius: 50%;
  animation: rcp-bounce 1s ease-in-out infinite;
}

.rcp-thinking-dot:nth-child(2) {
  animation-delay: 0.15s;
}

.rcp-thinking-dot:nth-child(3) {
  animation-delay: 0.3s;
}

.rcp-thinking-text {
  margin-inline-start: 4px;
  font-size: 12px;
}

@keyframes rcp-bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.rcp-error {
  background: var(--wi-error-container, var(--wi-surface));
  color: var(--wi-error);
  border: 1px solid var(--wi-error);
  padding: 8px 10px;
  border-radius: var(--wi-radius-sm);
  font-size: 12px;
}

.rcp-input-row {
  border-top: 1px solid var(--wi-outline-variant);
  padding: var(--wi-space-sm) var(--wi-space-md);
  display: flex;
  align-items: flex-end;
  gap: var(--wi-space-sm);
  background: var(--wi-surface);
}

.rcp-textarea {
  flex: 1;
  resize: none;
  min-height: 44px;
  max-height: 120px;
  padding: 8px 10px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-sm);
  font-family: var(--wi-font-body);
  font-size: 13px;
  line-height: 1.5;
  color: var(--wi-on-surface);
  background: var(--wi-bg);
  outline: none;
  transition: border-color var(--ms-transition);
}

.rcp-textarea:focus {
  border-color: var(--wi-primary-container);
}

.rcp-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.rcp-send-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 0;
  border-radius: var(--wi-radius-sm);
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  font-family: var(--wi-font-body);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background var(--ms-transition), opacity var(--ms-transition);
  flex-shrink: 0;
}

.rcp-send-btn:hover:not(:disabled) {
  filter: brightness(0.95);
}

.rcp-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Slide animation */
.rcp-slide-enter-active,
.rcp-slide-leave-active {
  transition: transform 0.28s ease, opacity 0.28s ease;
}

.rcp-slide-enter-from,
.rcp-slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* In RTL the panel slides in from the left edge instead of the right. */
:global([dir='rtl']) .rcp-panel {
  inset-inline-end: 0;
}

:global([dir='rtl']) .rcp-slide-enter-from,
:global([dir='rtl']) .rcp-slide-leave-to {
  transform: translateX(-100%);
}

@media (max-width: 600px) {
  .rcp-panel {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .rcp-slide-enter-active,
  .rcp-slide-leave-active {
    transition: none;
  }
  .rcp-thinking-dot {
    animation: none;
  }
}
</style>
