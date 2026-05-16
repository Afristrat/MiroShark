<template>
  <!-- ═══════════════════════════════════════════════════════════
       US-107 — Console upload privative (/console)
       Extraction depuis Home.vue : la « console graines de réalité »
       (upload, fetch URL, TrendingTopics, ScenarioSuggestions,
       textarea prompt, bouton Lancer) ne vit plus sur la home
       publique. Elle a maintenant sa propre route, gardée par
       requiresAuth + requiresSelfService.
       ═══════════════════════════════════════════════════════════ -->
  <div class="console-page">
    <SettingsPanel :open="settingsOpen" @close="settingsOpen = false" />

    <!-- Document preview modal (URL fetches + Ask-mode generations) -->
    <Teleport to="body">
      <div v-if="previewDoc" class="doc-preview-overlay" @click.self="previewDoc = null">
        <div class="doc-preview-modal">
          <div class="doc-preview-header">
            <div class="doc-preview-title">
              <span class="doc-preview-icon">◈</span>
              <span>{{ previewDoc.title }}</span>
            </div>
            <button class="doc-preview-close" @click="previewDoc = null">✕</button>
          </div>
          <div class="doc-preview-warning"></div>
          <div class="doc-preview-meta">
            {{ $t('home.preview.chars', { count: previewDoc.char_count.toLocaleString() }) }}
            <span v-if="previewDoc.url" class="doc-preview-meta-sep">·</span>
            <span v-if="previewDoc.url" class="doc-preview-url">{{ previewDoc.url }}</span>
          </div>
          <pre class="doc-preview-body">{{ previewDoc.text }}</pre>
        </div>
      </div>
    </Teleport>

    <main class="console-main">
      <!-- Hero introductif -->
      <header class="console-hero">
        <div class="console-hero-eyebrow">{{ $t('console.eyebrow') }}</div>
        <h1 class="console-hero-title">{{ $t('home.panel.consoleTitle') }}</h1>
        <p class="console-hero-subtitle">{{ $t('home.panel.consoleSubtitle') }}</p>
      </header>

      <!-- Dashboard 2 colonnes : statut + console -->
      <section class="dashboard-section">
        <!-- Left Column: Status & Steps -->
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">■</span> {{ $t('home.panel.systemStatus') }}
          </div>

          <h2 class="section-title">{{ $t('home.panel.ready') }}</h2>
          <p class="section-desc">{{ $t('home.panel.readyDesc') }}</p>

          <div class="steps-container">
            <div class="steps-header">
              <span class="diamond-icon">◇</span> {{ $t('home.steps.title') }}
            </div>
            <div class="workflow-list">
              <div class="workflow-item">
                <span class="step-num">01</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.steps.s1.title') }}</div>
                  <div class="step-desc">{{ $t('home.steps.s1.desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">02</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.steps.s2.title') }}</div>
                  <div class="step-desc">{{ $t('home.steps.s2.desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">03</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.steps.s3.title') }}</div>
                  <div class="step-desc">{{ $t('home.steps.s3.desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">04</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.steps.s4.title') }}</div>
                  <div class="step-desc">{{ $t('home.steps.s4.desc') }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Interactive Console -->
        <div class="right-panel">
          <div class="console-box">
            <!-- Upload Area -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.console.seedsLabel') }}</span>
                <span class="console-meta">{{ $t('home.console.seedsMeta') }}</span>
              </div>

              <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />

                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon">↑</div>
                  <div class="upload-title">{{ $t('home.console.uploadTitle') }}</div>
                  <div class="upload-hint">{{ $t('home.console.uploadHint') }}</div>
                </div>

                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item">
                    <span class="file-icon">📄</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                  </div>
                </div>

                <div v-if="pdfScanWarnings.length > 0" class="pdf-scan-warning">
                  <span class="pdf-scan-icon" aria-hidden="true">⚠</span>
                  <div class="pdf-scan-body">
                    <strong>{{ $t('home.console.pdfScanTitle') }}</strong>
                    <span>{{ $t('home.console.pdfScanHint') }}</span>
                    <ul class="pdf-scan-files">
                      <li v-for="name in pdfScanWarnings" :key="name">{{ name }}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <!-- Ask Mode -->
            <div class="console-section url-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.console.askLabel') }}</span>
                <span class="console-meta">{{ $t('home.console.askMeta') }}</span>
              </div>
              <div class="url-input-row">
                <input
                  v-model="askQuestion"
                  class="url-input"
                  type="text"
                  :placeholder="$t('home.console.askPlaceholder')"
                  :disabled="loading || askBusy"
                  @keydown.enter.prevent="runAskMode"
                />
                <button
                  class="url-fetch-btn"
                  @click="runAskMode"
                  :disabled="!askQuestion.trim() || loading || askBusy"
                >
                  <span v-if="askBusy">...</span>
                  <span v-else>{{ $t('home.console.researchBtn') }}</span>
                </button>
              </div>
              <div v-if="askError" class="url-error">{{ askError }}</div>
              <div v-if="askEnriching" class="url-doc-meta" style="margin-top:6px">{{ $t('home.enriching') }}</div>
              <div v-else-if="askBusy" class="url-doc-meta" style="margin-top:6px">{{ $t('home.console.researchBusy') }}</div>
              <div v-if="askDocs.length > 0" class="url-doc-list">
                <div
                  v-for="doc in askDocs"
                  :key="doc.url"
                  class="url-doc-item"
                  role="button"
                  tabindex="0"
                  :title="$t('home.console.askDocTitle')"
                  @click="previewDoc = doc"
                  @keydown.enter.prevent="previewDoc = doc"
                  @keydown.space.prevent="previewDoc = doc"
                >
                  <span class="url-doc-icon">◈</span>
                  <div class="url-doc-info">
                    <div class="url-doc-title" :title="doc.title">{{ truncate(doc.title, 70) }}</div>
                    <div class="url-doc-meta" :title="doc.url">{{ $t('home.preview.chars', { count: doc.char_count.toLocaleString() }) }} · {{ truncate(doc.url, 72) }}</div>
                  </div>
                  <button @click.stop="removeUrlDocByRef(doc)" class="remove-btn">×</button>
                </div>
              </div>
            </div>

            <!-- URL Input Section -->
            <div class="console-section url-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.console.urlLabel') }}</span>
                <span class="console-meta">{{ $t('home.console.urlMeta') }}</span>
              </div>
              <div class="url-input-row">
                <input
                  v-model="urlInput"
                  class="url-input"
                  type="url"
                  :placeholder="$t('home.console.urlPlaceholder')"
                  :disabled="loading || urlFetching"
                  @keydown.enter.prevent="fetchUrlDoc"
                />
                <button
                  class="url-fetch-btn"
                  @click="fetchUrlDoc"
                  :disabled="!urlInput.trim() || loading || urlFetching"
                >
                  <span v-if="urlFetching">...</span>
                  <span v-else>{{ $t('home.console.fetchBtn') }}</span>
                </button>
              </div>
              <div v-if="urlError" class="url-error">{{ urlError }}</div>
              <div v-if="fetchedDocs.length > 0" class="url-doc-list">
                <div
                  v-for="doc in fetchedDocs"
                  :key="doc.url"
                  class="url-doc-item"
                  role="button"
                  tabindex="0"
                  :title="$t('home.console.urlDocTitle')"
                  @click="previewDoc = doc"
                  @keydown.enter.prevent="previewDoc = doc"
                  @keydown.space.prevent="previewDoc = doc"
                >
                  <span class="url-doc-icon">◈</span>
                  <div class="url-doc-info">
                    <div class="url-doc-title" :title="doc.title">{{ truncate(doc.title, 70) }}</div>
                    <div class="url-doc-meta" :title="doc.url">{{ $t('home.preview.chars', { count: doc.char_count.toLocaleString() }) }} · {{ truncate(doc.url, 72) }}</div>
                  </div>
                  <button @click.stop="removeUrlDocByRef(doc)" class="remove-btn">×</button>
                </div>
              </div>
              <TrendingTopics :busy="urlFetching" @select="handleTrendingSelect" />
            </div>

            <div class="console-divider">
              <span>{{ $t('home.console.params') }}</span>
            </div>

            <!-- Input Area -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.console.promptLabel') }}</span>
              </div>
              <ScenarioSuggestions
                :text-preview="scenarioSuggestPreview"
                :simulation-prompt="formData.simulationRequirement"
                @use="handleSuggestionUse"
              />
              <!-- F-Profile 2026-05-15 : selector scope_profile -->
              <div class="scope-profile-row">
                <label class="scope-profile-label" for="scope-profile-select">
                  {{ $t('home.console.scopeProfile.label') }}
                </label>
                <select
                  id="scope-profile-select"
                  v-model="selectedScopeProfile"
                  class="scope-profile-select"
                  :disabled="loading"
                  data-testid="scope-profile-select"
                >
                  <option
                    v-for="opt in availableScopeProfiles"
                    :key="opt.value || 'auto'"
                    :value="opt.value"
                  >{{ opt.labelKey ? $t(opt.labelKey) : opt.text }}</option>
                </select>
                <span
                  v-if="!selectedScopeProfile && autoScopeProfile"
                  class="scope-profile-hint"
                  :title="$t('home.console.scopeProfile.autoDetectedTooltip')"
                >
                  {{ $t('home.console.scopeProfile.autoDetected', { profile: autoScopeProfile }) }}
                </span>
              </div>
              <div class="input-wrapper">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="code-input"
                  :placeholder="$t('home.console.promptPlaceholder')"
                  rows="6"
                  :disabled="loading"
                  data-testid="seed-textarea"
                ></textarea>
                <div class="model-badge">{{ $t('home.console.engine') }}</div>
              </div>

              <!-- US-B04.1 — Toggle Kairos + panel research consomme 01 -->
              <label class="kairos-toggle">
                <input
                  v-model="researchEnabled"
                  type="checkbox"
                  class="kairos-toggle-input"
                  data-testid="kairos-toggle"
                />
                <span class="kairos-toggle-text">
                  <strong>{{ $t('home.console.research.toggleLabel') }}</strong>
                  <span class="kairos-toggle-hint">
                    {{ $t('home.console.research.toggleHint') }}
                  </span>
                </span>
              </label>

              <TopicResearchPanel
                v-if="researchEnabled"
                :session-id="researchSessionId"
                :status="researchStatus"
                :result="researchResult"
                :error-code="researchErrorCode"
                :elapsed-seconds="researchElapsed"
                :cached="researchCached"
                data-testid="research-panel"
                @compose="handleResearchCompose"
              />
            </div>

            <div class="console-section btn-section">
              <button
                class="start-engine-btn"
                @click="startSimulation"
                :disabled="!canSubmit || loading"
              >
                <span v-if="!loading">{{ $t('home.console.launch') }}</span>
                <span v-else>{{ $t('home.console.initializing') }}</span>
                <span class="btn-arrow">→</span>
              </button>
              <p
                v-if="canSubmitReason"
                class="start-engine-reason"
                data-testid="start-disabled-reason"
              >
                ⓘ {{ canSubmitReason }}
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- Galerie de templates + historique : conservés ici car cohérents
           avec un mode self-service. Visibles seulement aux utilisateurs
           qui ont déjà passé le guard de la route. -->
      <div id="templates-gallery">
        <TemplateGallery />
      </div>

      <HistoryDatabase />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import TemplateGallery from '../components/TemplateGallery.vue'
import SettingsPanel from '../components/SettingsPanel.vue'
import ScenarioSuggestions from '../components/ScenarioSuggestions.vue'
import TrendingTopics from '../components/TrendingTopics.vue'
import TopicResearchPanel from '../components/TopicResearchPanel.vue'
import { fetchUrl } from '../api/graph'
import { askMode, enrichAsk } from '../api/simulation'
import {
  getResearchStatus,
  getScopeProfiles,
  postResearchFromSeed,
} from '../api/research'

const { t, locale } = useI18n()
const router = useRouter()
const route = useRoute()

const settingsOpen = ref(false)
const previewDoc = ref(null)

// Form data
const formData = ref({
  simulationRequirement: ''
})

// ─── US-B03 — Recherche dynamique seed → topics ────────────────────────────
// Constantes du watcher : trigger seulement si seed assez longue + debounce.
const RESEARCH_SEED_MIN_CHARS = 60
const RESEARCH_DEBOUNCE_MS = 1500
const RESEARCH_POLL_INTERVAL_MS = 3000
// Max 6 min de polling (le pipeline Kairos prend ~170 s, +marge cold start).
const RESEARCH_POLL_TIMEOUT_MS = 6 * 60 * 1000

const researchSessionId = ref(null)
const researchStatus = ref('idle') // idle|starting|running|completed|failed|timeout|error
const researchResult = ref(null)
const researchErrorCode = ref(null)
const researchCached = ref(false)
const researchElapsed = ref(0)
// Dernier seed qui a déclenché un POST, pour éviter de re-trigger sur la
// même chaîne quand l'utilisateur navigue dans le textarea sans modifier.
const lastTriggeredSeed = ref('')

let researchDebounceTimer = null
let researchPollTimer = null
let researchElapsedTimer = null
let researchStartedAt = 0
let researchPollDeadline = 0

const files = ref([])
const urlInput = ref('')
const urlDocs = ref([])
const urlFetching = ref(false)
const urlError = ref('')

const askQuestion = ref('')
const askBusy = ref(false)
const askError = ref('')
const askEnriching = ref(false)

const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

// Pré-remplir l'URL si ?url= présent (depuis TrendingTopics ailleurs)
onMounted(async () => {
  const preloadUrl = route.query.url
  if (preloadUrl && typeof preloadUrl === 'string') {
    urlInput.value = preloadUrl
    fetchUrlDoc()
  }
  // A8 2026-05-16 — fetch dynamiquement la liste des scope_profiles depuis Kairos.
  // En cas d'échec, la liste fallback hardcodée reste affichée (cf. availableScopeProfiles).
  try {
    const res = await getScopeProfiles()
    if (res?.success && Array.isArray(res.data?.profiles)) {
      fetchedScopeProfiles.value = res.data.profiles
    }
  } catch (err) {
    // best-effort : log côté console mais ne pas bloquer l'UI
    // eslint-disable-next-line no-console
    console.warn('[ConsoleView] getScopeProfiles failed, falling back to hardcoded list:', err)
  }
})

const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' &&
    (files.value.length > 0 || urlDocs.value.length > 0)
})

// US-B04.1 — message explicatif quand canSubmit est false. Permet d'éviter
// que l'utilisateur clique « Lancer » dans le vide sans savoir pourquoi
// le bouton est grisé.
const canSubmitReason = computed(() => {
  if (canSubmit.value || loading.value) return null
  const hasMatiere = files.value.length > 0 || urlDocs.value.length > 0
  if (!hasMatiere) return t('home.console.disabledReason.noSeeds')
  if (!formData.value.simulationRequirement.trim()) {
    return t('home.console.disabledReason.noPrompt')
  }
  return null
})

// US-B04.1 — toggle pour activer/désactiver la consommation Kairos.
// Par défaut activé. Si désactivé : aucun appel POST/GET vers
// /api/research/* — le panel reste idle.
const researchEnabled = ref(true)

const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

const handleDragOver = () => {
  if (!loading.value) isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

const filePreviewText = ref('')
const pdfScanWarnings = ref([])

const _extractPdfPreview = async (file) => {
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/simulation/file-preview', { method: 'POST', body: fd })
    if (!res.ok) return ''
    const json = await res.json()
    const text = (json?.data?.text || '').slice(0, 3000)
    if (text.length < 80 && file.name.toLowerCase().endsWith('.pdf')) {
      pdfScanWarnings.value.push(file.name)
    }
    return text
  } catch (_) {
    return ''
  }
}

const refreshFilePreviewText = async () => {
  const textish = files.value.filter(f => {
    const ext = (f.name.split('.').pop() || '').toLowerCase()
    return ext === 'md' || ext === 'txt'
  })
  const pdfs = files.value.filter(f =>
    (f.name.split('.').pop() || '').toLowerCase() === 'pdf'
  )
  try {
    const textChunks = await Promise.all(textish.map(async (f) => {
      try {
        const slice = f.slice ? f.slice(0, 6000) : f
        const txt = await slice.text()
        return (txt || '').slice(0, 3000)
      } catch (_) { return '' }
    }))
    const pdfChunks = await Promise.all(pdfs.map(_extractPdfPreview))
    const all = [...textChunks, ...pdfChunks].filter(Boolean)
    filePreviewText.value = all.join('\n\n').slice(0, 6000)
  } catch (_) {
    filePreviewText.value = ''
  }
}

const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
  pdfScanWarnings.value = []
  refreshFilePreviewText()
}

const removeFile = (index) => {
  files.value.splice(index, 1)
  pdfScanWarnings.value = []
  refreshFilePreviewText()
}

const scenarioSuggestPreview = computed(() => {
  const urlChunks = (urlDocs.value || [])
    .map(d => {
      const head = d.title ? `# ${d.title}\n` : ''
      const body = (d.text || '').slice(0, 3000)
      return body ? head + body : ''
    })
    .filter(Boolean)
  const combined = [...urlChunks]
  if (filePreviewText.value) combined.push(filePreviewText.value)
  return combined.join('\n\n').slice(0, 6000)
})

const handleSuggestionUse = ({ question, simulationRequirement }) => {
  if (!question) return
  formData.value.simulationRequirement = simulationRequirement || question
}

const fetchUrlDoc = async () => {
  const url = urlInput.value.trim()
  if (!url || urlFetching.value) return
  if (urlDocs.value.some(d => d.url === url)) {
    urlError.value = t('home.console.duplicateUrl')
    return
  }
  urlFetching.value = true
  urlError.value = ''
  try {
    const res = await fetchUrl(url)
    if (res.success) {
      urlDocs.value.push(res.data)
      urlInput.value = ''
    } else {
      urlError.value = res.error || t('home.console.fetchFailed')
    }
  } catch (err) {
    urlError.value = err.message || t('home.console.fetchFailed')
  } finally {
    urlFetching.value = false
  }
}

const runAskMode = async () => {
  const q = askQuestion.value.trim()
  if (!q || askBusy.value) return
  askBusy.value = true
  askError.value = ''

  let enrichedQuestion = q
  try {
    askEnriching.value = true
    const enrichRes = await enrichAsk(q)
    if (enrichRes?.data?.context) {
      enrichedQuestion = `${q}\n\n--- Web Context ---\n${enrichRes.data.context}`
    }
  } catch (_) {
    // enrichissement non bloquant
  } finally {
    askEnriching.value = false
  }

  try {
    const res = await askMode(enrichedQuestion)
    if (!res.success) {
      askError.value = res.error || t('home.console.askFailed')
      return
    }
    const d = res.data
    const synthUrl = `bassira://ask/${encodeURIComponent(q.slice(0, 64))}`
    const idx = urlDocs.value.findIndex(x => x.url === synthUrl)
    const payload = {
      title: d.title,
      url: synthUrl,
      text: d.seed_document,
      char_count: (d.seed_document || '').length,
    }
    if (idx >= 0) urlDocs.value.splice(idx, 1, payload)
    else urlDocs.value.push(payload)
    if (!formData.value.simulationRequirement) {
      formData.value.simulationRequirement = d.simulation_requirement
    }
    askQuestion.value = ''
  } catch (err) {
    askError.value = err?.response?.data?.error || err?.message || t('home.console.askFailed')
  } finally {
    askBusy.value = false
  }
}

const handleTrendingSelect = ({ url }) => {
  if (!url || urlFetching.value) return
  if (urlDocs.value.some(d => d.url === url)) {
    urlError.value = t('home.console.alreadyLoadedUrl')
    return
  }
  urlInput.value = url
  urlError.value = ''
  fetchUrlDoc()
}

const removeUrlDocByRef = (doc) => {
  const idx = urlDocs.value.indexOf(doc)
  if (idx >= 0) urlDocs.value.splice(idx, 1)
}

const truncate = (s, max) => {
  if (!s) return ''
  return s.length > max ? s.slice(0, max - 1).trimEnd() + '…' : s
}

const askDocs = computed(() =>
  urlDocs.value.filter(d => typeof d.url === 'string' && d.url.startsWith('bassira://ask/'))
)
const fetchedDocs = computed(() =>
  urlDocs.value.filter(d => !(typeof d.url === 'string' && d.url.startsWith('bassira://ask/')))
)

// ─── US-B03 — Recherche dynamique : watcher + polling ──────────────────────

// F-Profile 2026-05-15 — l'utilisateur peut forcer un scope_profile
// pré-curé côté Kairos (table scope_profiles). null = pas de sélection
// manuelle ; on retombe sur autoScopeProfile.
const selectedScopeProfile = ref(null)

// A8 2026-05-16 — profils fetchés dynamiquement depuis Kairos au mount.
// Fallback sur la liste hardcodée si fetch échoue (Kairos indispo, etc.).
const fetchedScopeProfiles = ref([])

const availableScopeProfiles = computed(() => {
  const auto = { value: null, labelKey: 'home.console.scopeProfile.auto', text: null }
  const out = [auto]
  if (fetchedScopeProfiles.value.length > 0) {
    for (const p of fetchedScopeProfiles.value) {
      out.push({
        value: p.name,
        labelKey: null,
        text: p.description || p.name,
      })
    }
  } else {
    // Fallback baseline (correspond aux 2 profils seedés côté Kairos)
    out.push({
      value: 'morocco-tech',
      labelKey: 'home.console.scopeProfile.moroccoTech',
      text: null,
    })
    out.push({
      value: 'mena-business',
      labelKey: 'home.console.scopeProfile.menaBusiness',
      text: null,
    })
  }
  return out
})

// Auto-détection à partir du seed : mots-clés Maroc → morocco-tech,
// mots-clés MENA / Maghreb / GCC → mena-business. Évite à l'utilisateur
// d'oublier le selector.
const autoScopeProfile = computed(() => {
  const seed = String(formData.value?.simulationRequirement || '').toLowerCase()
  if (!seed || seed.length < 10) return null
  const moroccoKeywords = ['maroc', 'morocco', 'casablanca', 'rabat', 'marrakech', 'tanger', 'marocain']
  const menaKeywords = ['mena', 'maghreb', 'tunisi', 'algéri', 'egypt', 'égypt', 'gcc', 'gulf', 'arabie', 'émirat', 'eau', 'uae', 'qatar', 'arab']
  if (moroccoKeywords.some(k => seed.includes(k))) return 'morocco-tech'
  if (menaKeywords.some(k => seed.includes(k))) return 'mena-business'
  return null
})

const _stopResearchTimers = () => {
  if (researchPollTimer) {
    clearTimeout(researchPollTimer)
    researchPollTimer = null
  }
  if (researchElapsedTimer) {
    clearInterval(researchElapsedTimer)
    researchElapsedTimer = null
  }
}

const _isPipelineActive = () =>
  researchStatus.value === 'starting' || researchStatus.value === 'running'

const _pickLang = () => {
  const loc = String(locale.value || 'fr').toLowerCase()
  if (loc.startsWith('ar')) return 'ar'
  if (loc.startsWith('en')) return 'en'
  return 'fr'
}

const _pollResearch = async () => {
  if (!researchSessionId.value) return
  if (Date.now() > researchPollDeadline) {
    researchStatus.value = 'timeout'
    _stopResearchTimers()
    return
  }
  try {
    const res = await getResearchStatus(researchSessionId.value)
    if (!res || res.success === false) {
      researchStatus.value = 'error'
      researchErrorCode.value = res?.error_code || 'UNKNOWN'
      _stopResearchTimers()
      return
    }
    const d = res.data || {}
    const next = String(d.status || '').toLowerCase()
    researchCached.value = !!d.cached
    if (next === 'completed') {
      researchStatus.value = 'completed'
      researchResult.value = d.result || null
      _stopResearchTimers()
      return
    }
    if (next === 'failed' || next === 'timeout') {
      researchStatus.value = next
      researchErrorCode.value = (d.error_detail && d.error_detail.code) || null
      _stopResearchTimers()
      return
    }
    // Toujours running — réarmer le timer pour le prochain tick.
    researchPollTimer = setTimeout(_pollResearch, RESEARCH_POLL_INTERVAL_MS)
  } catch (err) {
    researchStatus.value = 'error'
    researchErrorCode.value = err?.response?.data?.error_code || 'UNKNOWN'
    _stopResearchTimers()
  }
}

const _triggerResearch = async (seed) => {
  // Idempotence : si même seed que la dernière fois, ne rien faire.
  if (lastTriggeredSeed.value === seed) return
  lastTriggeredSeed.value = seed
  // Reset complet de l'état avant nouveau lancement.
  _stopResearchTimers()
  researchSessionId.value = null
  researchResult.value = null
  researchErrorCode.value = null
  researchCached.value = false
  researchElapsed.value = 0
  researchStatus.value = 'starting'
  researchStartedAt = Date.now()
  researchPollDeadline = researchStartedAt + RESEARCH_POLL_TIMEOUT_MS
  researchElapsedTimer = setInterval(() => {
    researchElapsed.value = Math.floor((Date.now() - researchStartedAt) / 1000)
  }, 1000)
  try {
    // F-Profile 2026-05-15 — laisser l'utilisateur forcer un scope_profile
    // ('morocco-tech', 'mena-business') via select UI, sinon auto-détection
    // par mots-clés du seed.
    const effectiveProfile = selectedScopeProfile.value || autoScopeProfile.value || null
    const reqBody = { seed, lang: _pickLang() }
    if (effectiveProfile) reqBody.scope_profile = effectiveProfile
    const res = await postResearchFromSeed(reqBody)
    if (!res || res.success === false) {
      researchStatus.value = 'error'
      researchErrorCode.value = res?.error_code || 'UNKNOWN'
      _stopResearchTimers()
      return
    }
    const d = res.data || {}
    researchSessionId.value = d.session_id || null
    researchCached.value = !!d.cached
    if (!researchSessionId.value) {
      researchStatus.value = 'error'
      researchErrorCode.value = 'NO_SESSION_ID'
      _stopResearchTimers()
      return
    }
    researchStatus.value = 'running'
    // Premier poll après 1s plutôt que 3 (cache hit Bassira → completed
    // déjà disponible). Les ticks suivants restent à 3s.
    researchPollTimer = setTimeout(_pollResearch, 1000)
  } catch (err) {
    researchStatus.value = 'error'
    researchErrorCode.value = err?.response?.data?.error_code || 'UNKNOWN'
    _stopResearchTimers()
  }
}

// US-B04.1 — la recherche Kairos consomme la matière de 01 (files +
// URLs + ask docs) plutôt que le prompt 02. Sémantiquement, la graine
// = ce que l'utilisateur a déjà déposé, pas son intention de simulation.
// On watch directement scenarioSuggestPreview qui agrège déjà ces 3 sources.
watch(
  () => [scenarioSuggestPreview.value, researchEnabled.value],
  ([seedRaw, enabled]) => {
    if (researchDebounceTimer) {
      clearTimeout(researchDebounceTimer)
      researchDebounceTimer = null
    }
    // Toggle off → on ne déclenche jamais. On laisse un éventuel
    // résultat précédent visible (le user décide de le purger en
    // toggle on/off).
    if (!enabled) return
    const seed = (seedRaw || '').trim()
    // Tant qu'un pipeline est actif, on ne (re)déclenche pas — laisse-le
    // finir. L'utilisateur peut continuer à enrichir 01 sans casser
    // le polling courant.
    if (_isPipelineActive()) return
    if (seed.length < RESEARCH_SEED_MIN_CHARS) return
    researchDebounceTimer = setTimeout(() => {
      _triggerResearch(seed)
    }, RESEARCH_DEBOUNCE_MS)
  },
  { immediate: true },
)

/**
 * US-B04.2 — quand l'user clique « Insérer », le panel envoie :
 *   - prompt   : le markdown composé éditable (devient 1er urlDoc)
 *   - selections : variants Kairos sélectionnés (mode complet)
 *   - sources  : signaux cochés avec leurs URLs → 1 urlDoc par source
 *
 * Pourquoi N urlDocs au lieu d'un seul markdown : le backend simulation
 * Bassira ingère chaque urlDoc comme matière séparée (graphe Neo4j,
 * embedding, etc.). En réduisant tout à du markdown, les URLs des
 * sources ne sont pas réellement fetchées/comptées. En les exposant
 * comme urlDocs distincts, elles deviennent de vraies entrées 01.
 *
 * Déduplication : on ne ré-insère pas une URL déjà présente dans urlDocs.
 */
const handleResearchCompose = ({ prompt, selections, sources }) => {
  const compiled = (prompt || '').trim()
  if (!compiled) return

  // 1) Le brief composé (markdown éditable) — toujours créé en 01.
  const firstSel = Array.isArray(selections) && selections.length > 0 ? selections[0] : null
  const labelHead = firstSel?.topic_label ? firstSel.topic_label.slice(0, 60) : 'composé'
  const briefUrl = `bassira://research/${Date.now().toString(36)}`
  urlDocs.value.push({
    title: t('home.console.research.briefDocTitle', { topic: labelHead }),
    url: briefUrl,
    text: compiled,
    char_count: compiled.length,
  })

  // 2) Chaque source cochée devient un urlDoc indépendant — pour que la
  // simulation ingère vraiment les liens (et pas seulement la mention
  // markdown).
  const sourcesArr = Array.isArray(sources) ? sources : []
  const existingUrls = new Set(urlDocs.value.map((d) => d.url))
  for (const src of sourcesArr) {
    if (!src || !src.url || existingUrls.has(src.url)) continue
    const titleParts = []
    if (src.title) titleParts.push(src.title)
    else if (src.source) titleParts.push(src.source)
    else titleParts.push(src.url)
    const text = src.excerpt || src.title || src.url
    urlDocs.value.push({
      title: titleParts.join(' — ').slice(0, 200),
      url: src.url,
      text,
      char_count: text.length,
    })
    existingUrls.add(src.url)
  }

  // L'aperçu 01 va re-trigger scenarioSuggestPreview → on aligne
  // lastTriggeredSeed pour éviter qu'on relance un pipeline.
  lastTriggeredSeed.value = (scenarioSuggestPreview.value || '').trim()
}

onBeforeUnmount(() => {
  if (researchDebounceTimer) {
    clearTimeout(researchDebounceTimer)
    researchDebounceTimer = null
  }
  _stopResearchTimers()
})

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement, urlDocs.value)
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
/* Console — réutilise la palette Warm Intelligence + tokens existants */
.console-page {
  min-height: 100vh;
  background: var(--wi-bg);
  font-family: var(--ms-font-body);
  color: var(--wi-on-bg);
}

.console-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--ms-space-12) var(--ms-space-6);
}

/* Hero introductif (remplace le hero Home + le sous-titre console) */
.console-hero {
  text-align: center;
  margin: 0 auto var(--ms-space-10) auto;
  max-width: 880px;
}
.console-hero-eyebrow {
  display: inline-block;
  padding: 6px var(--ms-space-4);
  background: var(--wi-primary-soft);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-heading);
  font-size: 12px;
  font-weight: 600;
  color: var(--wi-primary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: var(--ms-space-4);
}
.console-hero-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h1-size);
  font-weight: var(--wi-h1-weight);
  line-height: var(--wi-h1-leading);
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-bg);
  margin: 0 0 var(--ms-space-3) 0;
}
.console-hero-subtitle {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  color: var(--wi-on-surface-variant);
  margin: 0;
}

/* Dashboard 2-cols (identique à Home.vue) */
.dashboard-section {
  display: flex;
  gap: var(--ms-space-8);
  align-items: flex-start;
}
.dashboard-section .left-panel,
.dashboard-section .right-panel {
  display: flex;
  flex-direction: column;
}
.left-panel {
  flex: 0.8;
  background: var(--wi-surface);
  border-radius: var(--wi-radius-card);
  border: 1px solid var(--wi-outline-variant);
  padding: var(--ms-space-6);
  box-shadow: var(--wi-shadow-ambient);
}
.panel-header {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  margin-bottom: var(--ms-space-4);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.status-dot { color: var(--wi-secondary); font-size: 0.8rem; }
.section-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  line-height: var(--wi-h3-leading);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin: 0 0 var(--ms-space-2) 0;
}
.section-desc {
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  margin-bottom: var(--ms-space-6);
}
.steps-container {
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  padding: var(--ms-space-5);
  background: var(--wi-surface-container-low);
  position: relative;
}
.steps-header {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  margin-bottom: var(--ms-space-4);
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.diamond-icon { color: var(--wi-primary-container); font-size: 1rem; }
.workflow-list { display: flex; flex-direction: column; gap: var(--ms-space-4); }
.workflow-item { display: flex; align-items: flex-start; gap: var(--ms-space-4); }
.step-num {
  font-family: var(--ms-font-mono);
  font-weight: 600;
  font-size: 14px;
  color: var(--wi-primary);
  letter-spacing: 0.08em;
  min-width: 28px;
}
.step-info { flex: 1; }
.step-title {
  font-family: var(--wi-font-heading);
  font-size: 18px;
  font-weight: 500;
  color: var(--wi-on-surface);
  margin-bottom: 4px;
}
.step-desc {
  font-family: var(--wi-font-body);
  font-size: 14px;
  color: var(--wi-on-surface-variant);
  line-height: 1.6;
}

.right-panel { flex: 1.2; }
.console-box {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-inline-start: 4px solid var(--wi-primary-container);
  border-radius: var(--wi-radius-card);
  padding: var(--ms-space-2);
  position: relative;
  box-shadow: var(--wi-shadow-ambient);
}
.console-section { padding: var(--ms-space-4); }
.console-section.btn-section { padding-top: 0; }
.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--ms-space-2);
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-primary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.console-label { font-weight: 600; letter-spacing: 0.12em; }
.console-meta {
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  text-transform: none;
  letter-spacing: 0;
}

.upload-zone {
  border: 2px dashed var(--wi-outline-variant);
  border-radius: var(--ms-radius-md);
  height: 200px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: var(--ms-transition);
  background: var(--wi-surface-container-low);
}
.upload-zone.has-files { align-items: flex-start; }
.upload-zone:hover {
  border-color: var(--wi-primary-container);
  background: var(--wi-surface);
}
.upload-zone.drag-over {
  border-color: var(--wi-secondary);
  background: var(--ms-mint-soft);
}
.upload-placeholder { text-align: center; }
.upload-icon {
  width: 48px;
  height: 48px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--ms-space-2);
  color: var(--wi-primary);
  font-size: 1.4rem;
  background: var(--wi-surface);
}
.upload-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin-bottom: 4px;
}
.upload-hint {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
}

.file-list {
  width: 100%;
  padding: var(--ms-space-2);
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-1);
}
.file-item {
  display: flex;
  align-items: center;
  background: var(--wi-surface);
  padding: var(--ms-space-1) var(--ms-space-2);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--ms-radius-sm);
  font-family: var(--ms-font-mono);
  font-size: 14px;
  color: var(--wi-on-surface);
}
.file-name { flex: 1; margin: 0 var(--ms-space-2); }
.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: var(--wi-on-surface-variant);
  transition: var(--ms-transition-fast);
}
.remove-btn:hover { color: var(--wi-error); }

.console-divider {
  display: flex;
  align-items: center;
  margin: var(--ms-space-2) 0;
}
.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--ms-border);
}
.console-divider span {
  padding: 0 var(--ms-space-2);
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--ms-text-subtle);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.input-wrapper {
  position: relative;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--ms-radius-md);
  background: var(--wi-surface-container-low);
  transition: var(--ms-transition-fast);
}
.input-wrapper:focus-within {
  border-color: var(--wi-primary-container);
  box-shadow: 0 0 0 3px var(--ms-orange-soft);
}

/* F-Profile : selector scope_profile au-dessus de la textarea */
.scope-profile-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 8px;
  flex-wrap: wrap;
  font-family: var(--ms-font-mono);
  font-size: 12px;
}
.scope-profile-label {
  color: var(--ms-text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.scope-profile-select {
  font-family: inherit;
  font-size: 12px;
  padding: 3px 8px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--ms-radius-md);
  background: var(--wi-surface-container-low);
  color: var(--wi-on-surface);
  cursor: pointer;
  transition: var(--ms-transition-fast);
}
.scope-profile-select:hover,
.scope-profile-select:focus {
  border-color: var(--wi-primary-container);
  outline: none;
}
.scope-profile-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.scope-profile-hint {
  color: var(--wi-on-primary-container, #b34a1f);
  font-style: italic;
  font-size: 11px;
}
.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: var(--ms-space-4);
  font-family: var(--ms-font-mono);
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 150px;
  color: var(--wi-on-surface);
}
.code-input::placeholder { color: var(--ms-text-subtle); }
.model-badge {
  position: absolute;
  bottom: var(--ms-space-1);
  inset-inline-end: var(--ms-space-2);
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--ms-text-subtle);
  letter-spacing: 0.06em;
}

.start-engine-btn {
  width: 100%;
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: 2px solid var(--wi-primary);
  border-radius: var(--wi-radius-pill);
  padding: 16px var(--ms-space-6);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.15s ease;
  letter-spacing: 0.02em;
  position: relative;
  overflow: hidden;
  box-shadow: var(--wi-shadow-md);
}
.start-engine-btn:hover:not(:disabled) {
  background: var(--wi-primary-container);
  border-color: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  box-shadow: var(--wi-shadow-lg);
}
.start-engine-btn:active:not(:disabled) { opacity: 0.92; }
.start-engine-btn:disabled {
  background: var(--ms-bg-muted);
  color: var(--ms-text-subtle);
  cursor: not-allowed;
  border-color: var(--ms-border);
  box-shadow: none;
}
.start-engine-reason {
  margin: var(--ms-space-2) 0 0 0;
  font-size: 12px;
  color: var(--wi-primary-container);
  text-align: center;
  font-style: italic;
}

/* US-B04.1 — Toggle Kairos juste après la textarea 02. */
.kairos-toggle {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px var(--ms-space-3);
  margin-top: var(--ms-space-3);
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md, 8px);
  cursor: pointer;
  transition: border-color var(--ms-transition-fast);
}
.kairos-toggle:hover {
  border-color: var(--wi-primary-container);
}
.kairos-toggle-input {
  margin-top: 3px;
  width: 18px;
  height: 18px;
  accent-color: var(--wi-primary-container);
  cursor: pointer;
  flex-shrink: 0;
}
.kairos-toggle-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.kairos-toggle-text strong {
  font-size: 13px;
  font-weight: 600;
  color: var(--wi-on-surface);
}
.kairos-toggle-hint {
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  font-style: italic;
}

.url-section { padding-top: 0; }
.url-input-row { display: flex; gap: var(--ms-space-2); }
.url-input {
  flex: 1;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--ms-radius-sm);
  background: var(--wi-surface-container-low);
  padding: var(--ms-space-2) var(--ms-space-3);
  font-family: var(--ms-font-mono);
  font-size: 13px;
  color: var(--wi-on-surface);
  outline: none;
  transition: var(--ms-transition-fast);
  min-width: 0;
}
.url-input:focus {
  border-color: var(--wi-primary-container);
  background: var(--wi-surface);
  box-shadow: 0 0 0 3px var(--ms-orange-soft);
}
.url-input::placeholder { color: var(--ms-text-subtle); }
.url-input:disabled { opacity: 0.5; cursor: not-allowed; }
.url-fetch-btn {
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
  border: 1px solid var(--wi-secondary);
  border-radius: var(--ms-radius-sm);
  padding: var(--ms-space-2) var(--ms-space-3);
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: var(--ms-transition-fast);
  white-space: nowrap;
}
.url-fetch-btn:hover:not(:disabled) {
  background: var(--wi-on-secondary-container);
  border-color: var(--wi-on-secondary-container);
}
.url-fetch-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.url-error {
  margin-top: var(--ms-space-1);
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-error);
}
.url-doc-list {
  margin-top: var(--ms-space-2);
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-1);
}
.url-doc-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ms-space-2);
  background: var(--wi-surface);
  padding: var(--ms-space-2) var(--ms-space-3);
  border: 1px solid var(--wi-outline-variant);
  border-inline-start: 3px solid var(--wi-secondary);
  border-radius: var(--ms-radius-sm);
  cursor: pointer;
  transition: background var(--ms-transition-fast), border-inline-start-color var(--ms-transition-fast);
}
.url-doc-item:hover,
.url-doc-item:focus-visible {
  background: var(--ms-mint-soft);
  border-inline-start-color: var(--wi-primary-container);
  outline: none;
}
.url-doc-icon {
  color: var(--wi-secondary);
  font-size: 14px;
  margin-top: 1px;
  flex-shrink: 0;
}
.url-doc-info { flex: 1; min-width: 0; }
.url-doc-title {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 500;
  color: var(--wi-on-surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.url-doc-meta {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Doc Preview Modal */
.doc-preview-overlay {
  position: fixed;
  inset: 0;
  background: var(--ms-bg-overlay);
  z-index: var(--ms-z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--ms-space-8);
  animation: doc-preview-fade 0.12s ease-out;
}
@keyframes doc-preview-fade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.doc-preview-modal {
  background: var(--wi-surface);
  width: 760px;
  max-width: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: var(--wi-radius-card);
  border: 1px solid var(--wi-outline-variant);
  box-shadow: var(--wi-shadow-lg);
  overflow: hidden;
  font-family: var(--ms-font-mono);
}
.doc-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ms-space-3);
  padding: var(--ms-space-4) var(--ms-space-5);
  background: var(--wi-on-bg);
  color: var(--wi-surface);
}
.doc-preview-title {
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-preview-icon { color: var(--ms-mint); flex-shrink: 0; }
.doc-preview-close {
  background: none;
  border: none;
  color: var(--wi-surface-dim);
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  flex-shrink: 0;
  transition: color var(--ms-transition-fast);
}
.doc-preview-close:hover { color: var(--wi-surface); }
.doc-preview-warning {
  height: 6px;
  background: var(--wi-primary-container);
}
.doc-preview-meta {
  padding: var(--ms-space-3) var(--ms-space-5);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--wi-on-surface-variant);
  border-bottom: 1px solid var(--wi-outline-variant);
  overflow-wrap: anywhere;
}
.doc-preview-meta-sep { margin: 0 6px; }
.doc-preview-url { color: var(--wi-primary); }
.doc-preview-body {
  margin: 0;
  padding: var(--ms-space-5);
  flex: 1;
  overflow-y: auto;
  font-family: var(--ms-font-mono);
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--wi-on-surface);
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--wi-surface);
}

@media (max-width: 1024px) {
  .dashboard-section { flex-direction: column; }
}

.pdf-scan-warning {
  display: flex;
  gap: var(--ms-space-2);
  align-items: flex-start;
  background: var(--ms-peach-soft);
  border: 1px solid var(--ms-peach);
  border-radius: var(--ms-radius-sm);
  padding: var(--ms-space-2) var(--ms-space-3);
  margin-top: var(--ms-space-2);
  font-size: 13px;
  color: var(--ms-text);
}
.pdf-scan-icon { font-size: 1rem; flex-shrink: 0; color: var(--ms-peach); }
.pdf-scan-body { display: flex; flex-direction: column; gap: 4px; }
.pdf-scan-files { margin: 4px 0 0 var(--ms-space-4); padding: 0; list-style: disc; }
</style>
