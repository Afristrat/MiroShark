<template>
  <!--
    IntakeAgentPanel (US-IQ-02 frontend) — écran Assistant inline (PAS un
    panneau coulissant, contrairement à ReportChatPanel dont les classes
    CSS de base sont réutilisées). Bandeau IA permanent + chat + colonne
    latérale (brief live + sujets verrouillés) + bouton skip, conforme au
    prompt Stitch §10.2 (docs/intake/10-execution-prompts.md:83-104).
  -->
  <div class="iap-root">
    <div class="iap-banner">
      <span class="material-symbols-outlined iap-banner-icon" aria-hidden="true">smart_toy</span>
      <span>{{ $t('quote.step3.assistant.banner') }}</span>
    </div>

    <div class="iap-layout">
      <section class="iap-chat" aria-label="Assistant">
        <div ref="scrollEl" class="iap-messages">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="iap-message"
            :class="`is-${msg.role}`"
          >
            <span class="iap-message-role">
              {{ msg.role === 'user' ? $t('quote.step3.assistant.you') : $t('quote.step3.assistant.assistant') }}
            </span>
            <div class="iap-message-bubble">{{ msg.content }}</div>
          </div>

          <div v-if="isSending" class="iap-message is-assistant">
            <span class="iap-message-role">{{ $t('quote.step3.assistant.assistant') }}</span>
            <div class="iap-message-bubble is-thinking">
              <span class="iap-thinking-dot"></span>
              <span class="iap-thinking-dot"></span>
              <span class="iap-thinking-dot"></span>
              <span class="iap-thinking-text">{{ $t('quote.step3.assistant.thinking') }}</span>
            </div>
          </div>

          <div v-if="errorMsg" class="iap-error" role="alert">{{ errorMsg }}</div>
        </div>

        <form class="iap-input-row" @submit.prevent="onSubmit">
          <textarea
            v-model="draft"
            class="iap-textarea"
            rows="2"
            :placeholder="$t('quote.step3.assistant.placeholder')"
            :disabled="isSending || closed"
            @keydown.enter.exact.prevent="onSubmit"
          ></textarea>
          <button
            type="submit"
            class="iap-send-btn"
            :disabled="isSending || !draft.trim() || closed"
          >
            {{ isSending ? $t('quote.step3.assistant.sending') : $t('quote.step3.assistant.send') }}
          </button>
        </form>

        <button
          type="button"
          class="iap-skip-btn"
          :disabled="isSending || closed"
          @click="onSkip"
        >
          {{ $t('quote.step3.assistant.skipButton') }}
        </button>
      </section>

      <aside class="iap-sidebar" aria-label="Brief">
        <div class="iap-sidebar-block">
          <h3 class="iap-sidebar-title">{{ $t('quote.step3.assistant.briefSummaryTitle') }}</h3>
          <ul class="iap-brief-list">
            <li v-for="item in briefSummaryItems" :key="item.label">
              <strong>{{ item.label }}</strong> — {{ item.value }}
            </li>
          </ul>
        </div>

        <div v-if="lockedTopics.length > 0" class="iap-sidebar-block">
          <h3 class="iap-sidebar-title">{{ $t('quote.step3.assistant.lockedTopicsTitle') }}</h3>
          <ul class="iap-locked-list">
            <li v-for="(topic, idx) in lockedTopics" :key="idx">
              <span class="material-symbols-outlined iap-lock-icon" aria-hidden="true">lock</span>
              {{ topic.topic_label }}
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { postAgentTurn, completeIntakeSession } from '../api/intake'
import { formatApiError } from '../utils/error-handler'

const props = defineProps({
  sessionId: { type: String, required: true },
  brief: { type: Object, required: true },
  locale: { type: String, default: 'fr' },
})

const emit = defineEmits(['closed'])

const { t } = useI18n()

const messages = ref([])
const draft = ref('')
const isSending = ref(false)
const errorMsg = ref('')
const closed = ref(false)
const lockedTopics = ref([])
const scrollEl = ref(null)

const _AMORCE_BY_LOCALE = {
  fr: "Je suis prêt(e) à échanger sur mon brief.",
  en: "I'm ready to talk through my brief.",
  ar: "أنا مستعدّ للحديث عن ملفي.",
}

const briefSummaryItems = computed(() => {
  const b = props.brief || {}
  const items = []
  if (b.decision) items.push({ label: t('quote.temps1.a1.label'), value: b.decision })
  if (Array.isArray(b.options) && b.options.length > 0) {
    items.push({ label: t('quote.temps1.a2.label'), value: b.options.join(' / ') })
  }
  if (b.deadline && b.deadline.date) {
    items.push({ label: t('quote.temps1.a3.deadlineLabel'), value: b.deadline.date })
  }
  if (b.stakes && b.stakes.budget_bracket) {
    items.push({
      label: t('quote.temps3.a6.budgetLabel'),
      value: t(`quote.temps3.a6.budget.${b.stakes.budget_bracket}`),
    })
  }
  return items
})

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

const applyTurnResponse = (data) => {
  messages.value.push({ role: 'assistant', content: data.message })
  lockedTopics.value = data.confidential_flags || []
  scrollToBottom()
  if (data.close) {
    closed.value = true
    emit('closed', {
      route: data.route,
      calcomLink: data.calcom_link || null,
      packageRecommendation: data.package_recommendation || null,
    })
  }
}

const sendTurn = async (text) => {
  errorMsg.value = ''
  isSending.value = true
  try {
    const res = await postAgentTurn(props.sessionId, text)
    if (res?.data?.agent_unavailable) {
      closed.value = true
      emit('closed', {
        route: res.data.route,
        calcomLink: res.data.calcom_link || null,
        packageRecommendation: res.data.package_recommendation || null,
      })
      return
    }
    applyTurnResponse(res.data)
  } catch (err) {
    errorMsg.value = formatApiError(err, t)
  } finally {
    isSending.value = false
  }
}

const onSubmit = async () => {
  const text = draft.value.trim()
  if (!text || isSending.value || closed.value) return
  messages.value.push({ role: 'user', content: text })
  draft.value = ''
  scrollToBottom()
  await sendTurn(text)
}

const onSkip = async () => {
  if (isSending.value || closed.value) return
  isSending.value = true
  errorMsg.value = ''
  try {
    const res = await completeIntakeSession(props.sessionId)
    closed.value = true
    emit('closed', {
      route: res.data.route,
      calcomLink: res.data.calcom_link || null,
      packageRecommendation: res.data.package_recommendation || null,
    })
  } catch (err) {
    errorMsg.value = formatApiError(err, t)
  } finally {
    isSending.value = false
  }
}

onMounted(() => {
  const amorce = _AMORCE_BY_LOCALE[props.locale] || _AMORCE_BY_LOCALE.fr
  sendTurn(amorce)
})
</script>

<style scoped>
.iap-root {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}

.iap-banner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--wi-secondary-container);
  color: var(--wi-on-surface-variant);
  padding: 8px 14px;
  border-radius: var(--wi-radius-md);
  font-size: 12px;
  font-weight: 600;
  align-self: flex-start;
}
.iap-banner-icon {
  font-size: 16px !important;
}

.iap-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--wi-space-md);
}
@media (min-width: 720px) {
  .iap-layout {
    grid-template-columns: 1fr 320px;
  }
}

.iap-chat {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  min-width: 0;
}

.iap-messages {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  max-height: 420px;
  overflow-y: auto;
  padding: var(--wi-space-sm);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  background: var(--wi-bg);
}

.iap-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.iap-message.is-user {
  align-self: flex-end;
  max-width: 85%;
}
.iap-message.is-assistant {
  align-self: flex-start;
  max-width: 95%;
}

.iap-message-role {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--wi-outline);
}

.iap-message-bubble {
  padding: 10px 12px;
  border-radius: var(--wi-radius-card);
  font-size: 13px;
  line-height: 1.55;
  word-wrap: break-word;
}
.iap-message.is-user .iap-message-bubble {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
}
.iap-message.is-assistant .iap-message-bubble {
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  border: 1px solid var(--wi-outline-variant);
}

.iap-message-bubble.is-thinking {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--wi-on-surface-variant);
}
.iap-thinking-dot {
  width: 5px;
  height: 5px;
  background: var(--wi-on-primary-container);
  border-radius: 50%;
  animation: iap-bounce 1s ease-in-out infinite;
}
.iap-thinking-dot:nth-child(2) { animation-delay: 0.15s; }
.iap-thinking-dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes iap-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.iap-error {
  background: var(--wi-error-container, var(--wi-surface));
  color: var(--wi-error);
  border: 1px solid var(--wi-error);
  padding: 8px 10px;
  border-radius: var(--wi-radius-sm);
  font-size: 12px;
}

.iap-input-row {
  display: flex;
  align-items: flex-end;
  gap: var(--wi-space-sm);
}
.iap-textarea {
  flex: 1;
  resize: none;
  min-height: 44px;
  max-height: 120px;
  padding: 8px 10px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-sm);
  font-size: 13px;
  line-height: 1.5;
  color: var(--wi-on-surface);
  background: var(--wi-bg);
}
.iap-textarea:disabled { opacity: 0.6; }

.iap-send-btn {
  padding: 8px 14px;
  border: 0;
  border-radius: var(--wi-radius-sm);
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.iap-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.iap-skip-btn {
  align-self: flex-start;
  background: transparent;
  border: 1.5px solid var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
  font-size: 13px;
  font-weight: 600;
  padding: 10px 18px;
  border-radius: var(--wi-radius-interactive);
  cursor: pointer;
}
.iap-skip-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.iap-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}
.iap-sidebar-block {
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-sm);
  background: var(--wi-surface);
}
.iap-sidebar-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wi-on-surface-variant);
  margin: 0 0 8px 0;
}
.iap-brief-list,
.iap-locked-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: var(--wi-on-surface);
}
.iap-locked-list li {
  display: flex;
  align-items: center;
  gap: 6px;
}
.iap-lock-icon {
  font-size: 14px !important;
  color: var(--wi-outline);
}
</style>
