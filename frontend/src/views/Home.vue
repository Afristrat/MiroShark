<template>
  <div class="home-container">
    <!-- US-094 — La nav globale est désormais dans AppHeader.vue (App.vue),
         présente sur toutes les routes. Le bouton ⚙ Paramètres (admin/dev,
         config LLM) reste dans Home.vue mais à un emplacement discret pour
         ne pas polluer la nav publique : intégré au panneau console
         self-service masqué (cf. v-if showSelfServiceConsole). -->
    <SettingsPanel :open="settingsOpen" @close="settingsOpen = false" />
    <!-- Floating settings trigger — accessible via raccourci pour les admins
         qui ouvrent la home en mode dev. Caché aux visiteurs cold (opacité 0
         + pointer-events:none tant que l'utilisateur ne survole pas le bord
         bas-gauche de la viewport, cf. .home-settings-trigger). -->
    <button
      class="home-settings-trigger"
      @click="settingsOpen = true"
      :title="$t('home.nav.settingsTitle')"
      aria-label="Paramètres"
    >
      <span aria-hidden="true">⚙</span>
    </button>

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

    <div class="main-content">
      <!-- Upper Section: Hero Area — Stitch « Strategic Foresight » -->
      <section class="hero-section">
        <!-- Eyebrow pill : « بصيرة · Prospective stratégique » -->
        <div class="hero-eyebrow">
          <span class="hero-eyebrow-text">{{ $t('home.hero.eyebrow') }}</span>
        </div>

        <h1 class="main-title">
          <span class="gradient-text">{{ $t('home.hero.title') }}</span>
        </h1>

        <p class="hero-subtitle">{{ $t('home.hero.subtitle') }}</p>

        <!-- US-087 — CTAs orientés modèles publics + commande.
             Le self-service Step1-5 reste accessible techniquement (URLs
             directes /process, /simulation), mais on ne le promeut plus
             auprès des visiteurs cold : on les oriente vers les modèles
             publics ou la prise de contact commerciale. -->
        <div class="hero-cta-row">
          <router-link
            to="/models"
            class="hero-cta hero-cta--primary"
            :title="$t('home.heroCta.viewModelsTitle')"
          >
            <span>{{ $t('home.heroCta.viewModels') }}</span>
            <span class="hero-cta-arrow" aria-hidden="true">→</span>
          </router-link>
          <router-link
            to="/devis"
            class="hero-cta hero-cta--secondary"
            :title="$t('home.heroCta.orderAnalysisTitle')"
          >
            <span>{{ $t('home.heroCta.orderAnalysis') }}</span>
            <span class="hero-cta-arrow" aria-hidden="true">→</span>
          </router-link>
        </div>

        <!-- Trust strip : signaux Brier / sims / ISO -->
        <div class="hero-trust" role="list" :aria-label="$t('home.panel.systemStatus')">
          <span class="hero-trust-item hero-trust-mint" role="listitem">
            <span class="hero-trust-icon" aria-hidden="true">▲</span>
            <span>{{ $t('home.hero.trust.brier') }}</span>
          </span>
          <span class="hero-trust-sep" aria-hidden="true"></span>
          <span class="hero-trust-item hero-trust-orange" role="listitem">
            <span class="hero-trust-icon" aria-hidden="true">↗</span>
            <span>{{ $t('home.hero.trust.sims') }}</span>
          </span>
          <span class="hero-trust-sep" aria-hidden="true"></span>
          <span class="hero-trust-item hero-trust-mint" role="listitem">
            <span class="hero-trust-icon" aria-hidden="true">✓</span>
            <span>{{ $t('home.hero.trust.iso') }}</span>
          </span>
        </div>

        <!-- Punchline conservée pour Tier 2 Analyst (continuité éditoriale) -->
        <div class="hero-desc">
          <p>
            {{ $t('home.hero.descriptionPart1') }} <span class="highlight-bold">{{ $t('home.hero.brand') }}</span> {{ $t('home.hero.descriptionPart2') }} <span class="highlight-orange">{{ $t('home.hero.agents') }}</span> {{ $t('home.hero.descriptionPart3') }}
          </p>
          <p class="slogan-text">
            {{ $t('home.hero.slogan') }}<span class="blinking-cursor">_</span>
          </p>
        </div>

        <button class="scroll-down-btn" @click="scrollToBottom" :title="$t('home.hero.scrollDownTitle')">
          ↓
        </button>
      </section>

      <!-- Pivot models-first : SectorUseCases est désormais le bloc commercial
           principal de la home cold. 8 secteurs × 2 cas C-level → /models?sector=
           ou /devis?sector=&usecase=. Préserve la mécanique US-085 + relink US-087. -->
      <SectorUseCases />

      <!-- US-087 : console self-service masquée pour visiteurs cold,
           accès admin/client à venir US-088. Le bloc DOM est préservé
           intégralement (logique upload, ScenarioSuggestions, runAskMode,
           startSimulation) pour réactivation derrière un guard auth. -->
      <!-- Console Header : « Graines de réalité » (Stitch design) -->
      <header v-if="showSelfServiceConsole" id="reality-seeds-console" class="console-intro">
        <h2 class="console-intro-title">{{ $t('home.panel.consoleTitle') }}</h2>
        <p class="console-intro-subtitle">{{ $t('home.panel.consoleSubtitle') }}</p>
      </header>

      <!-- Lower Section: Two-Column Layout -->
      <section v-if="showSelfServiceConsole" class="dashboard-section">
        <!-- Left Column: Status & Steps -->
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">■</span> {{ $t('home.panel.systemStatus') }}
          </div>

          <h2 class="section-title">{{ $t('home.panel.ready') }}</h2>
          <p class="section-desc">
            {{ $t('home.panel.readyDesc') }}
          </p>


          <!-- What it does (from README) -->
          <div class="steps-container">
            <div class="steps-header">
               <span class="diamond-icon">◇</span> {{ $t('home.steps.title') }}
            </div>
            <div class="workflow-list">
              <div class="workflow-item" :ref="el => setStepCardRef(el, 0)">
                <span class="step-num">01</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.steps.s1.title') }}</div>
                  <div class="step-desc">{{ $t('home.steps.s1.desc') }}</div>
                </div>
              </div>
              <div class="workflow-item" :ref="el => setStepCardRef(el, 1)">
                <span class="step-num">02</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.steps.s2.title') }}</div>
                  <div class="step-desc">{{ $t('home.steps.s2.desc') }}</div>
                </div>
              </div>
              <div class="workflow-item" :ref="el => setStepCardRef(el, 2)">
                <span class="step-num">03</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.steps.s3.title') }}</div>
                  <div class="step-desc">{{ $t('home.steps.s3.desc') }}</div>
                </div>
              </div>
              <div class="workflow-item" :ref="el => setStepCardRef(el, 3)">
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

            <!-- Ask Mode (no document needed) -->
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
              <TrendingTopics
                :busy="urlFetching"
                @select="handleTrendingSelect"
              />
            </div>

            <!-- Divider -->
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
              <div class="input-wrapper">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="code-input"
                  :placeholder="$t('home.console.promptPlaceholder')"
                  rows="6"
                  :disabled="loading"
                ></textarea>
                <div class="model-badge">{{ $t('home.console.engine') }}</div>
              </div>
            </div>

            <!-- Start Button -->
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
            </div>
          </div>
        </div>
      </section>

      <!-- US-087 : TemplateGallery + HistoryDatabase masqués pour les visiteurs
           cold. Les templates correspondent au self-service Step1-5 (clic « Lancer »
           → /process), promotion stoppée sur la home publique au profit de /models.
           Réactivation derrière un guard auth admin/client à venir (US-088). -->
      <!-- Quick Start Templates -->
      <div v-if="showSelfServiceConsole" id="templates-gallery">
        <TemplateGallery />
      </div>

      <!-- History Project Database -->
      <HistoryDatabase v-if="showSelfServiceConsole" />

    </div>

    <!-- US-060 — Onboarding solo 4 étapes (premier visit uniquement) -->
    <OnboardingTour v-model="showOnboarding" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import TemplateGallery from '../components/TemplateGallery.vue'
import SettingsPanel from '../components/SettingsPanel.vue'
import ScenarioSuggestions from '../components/ScenarioSuggestions.vue'
import TrendingTopics from '../components/TrendingTopics.vue'
import OnboardingTour from '../components/OnboardingTour.vue'
import SectorUseCases from '../components/SectorUseCases.vue'
import { fetchUrl } from '../api/graph'
import { askMode, enrichAsk } from '../api/simulation'
import { useScrollFadeIn } from '../composables/useScrollFadeIn'
import { useAuthStore } from '../stores/auth'
import { storeToRefs } from 'pinia'
// US-094 — l'entrée auth adaptative (login / dashboard) est désormais
// portée par AppHeader.vue ; Home.vue n'a plus besoin du store auth.

// Refs for the 4 workflow step cards — populated via :ref callback in the
// template so the IntersectionObserver picks each one up individually.
const stepCardRefs = ref([])
const setStepCardRef = (el, idx) => {
  if (el) stepCardRefs.value[idx] = el
}
useScrollFadeIn(stepCardRefs)

const { t } = useI18n()

const settingsOpen = ref(false)
const previewDoc = ref(null)

// US-098 / US-099 — La console self-service (upload + Ask + URL + textarea +
// Lancer) et la galerie de templates ne sont visibles que pour :
//   1. Les super-admins Bassira (founders) — accès direct.
//   2. Les membres d'une org ayant `self_service_enabled = true`
//      (toggle sous contrôle Amine via /admin/analytics).
// Pour tous les autres visiteurs (cold ou clients standards), la home reste
// orientée découverte produit (CTA /models, /devis).
const authStore = useAuthStore()
const { isAuthenticated, isSuperAdmin, currentOrg } = storeToRefs(authStore)
const showSelfServiceConsole = computed(() => {
  if (isSuperAdmin.value) return true
  if (!isAuthenticated.value) return false
  return Boolean(currentOrg.value?.self_service_enabled)
})

// US-060 — Onboarding solo 4 étapes : visible uniquement au premier visit.
// Le flag `bassira_onboarding_done` est posé par OnboardingTour quand
// l'utilisateur clique Skip / Suivant final / Lancer un exemple.
const showOnboarding = ref(
  typeof window !== 'undefined' && !window.localStorage?.getItem('bassira_onboarding_done')
)

const router = useRouter()
const route = useRoute()

// US-058 — pré-remplir l'URL si ?url= présent (ex. clic depuis TrendingTopics dans SimulationView)
onMounted(() => {
  const preloadUrl = route.query.url
  if (preloadUrl && typeof preloadUrl === 'string') {
    urlInput.value = preloadUrl
    fetchUrlDoc()
  }
})

// US-087 — `scrollToTemplates` (US-044b) et `scrollToConsole` retirés :
// la galerie de templates et la console self-service ne sont plus exposées
// sur la home publique (cf. v-if="showSelfServiceConsole"). Le hero CTA
// route désormais vers /models et /devis.

// Form data
const formData = ref({
  simulationRequirement: ''
})

// File list
const files = ref([])

// URL import state
const urlInput = ref('')
const urlDocs = ref([])   // [{title, url, text, char_count}]
const urlFetching = ref(false)
const urlError = ref('')

// Ask-mode state — question-only pipeline
const askQuestion = ref('')
const askBusy = ref(false)
const askError = ref('')

// State
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)

// File input ref
const fileInput = ref(null)

// Computed: whether the form can be submitted
const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' &&
    (files.value.length > 0 || urlDocs.value.length > 0)
})

// Trigger file selection
const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

// Handle file selection
const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

// Handle drag-related events
const handleDragOver = (e) => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = (e) => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return
  
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

// File text previews — MD/TXT are read client-side; PDFs are sent to
// /api/simulation/file-preview (PyMuPDF server-side) so their content
// drives ScenarioSuggestions exactly like any other document type.
const filePreviewText = ref('')
const pdfScanWarnings = ref([]) // noms de fichiers PDF sans texte extractible (probablement scannés)

const _extractPdfPreview = async (file) => {
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/simulation/file-preview', { method: 'POST', body: fd })
    if (!res.ok) return ''
    const json = await res.json()
    const text = (json?.data?.text || '').slice(0, 3000)
    // Avertir si le PDF semble vide (< 80 chars = probablement un scan)
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

// Add files
const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
  pdfScanWarnings.value = [] // reset à chaque ajout de fichiers
  refreshFilePreviewText()
}

// Remove file
const removeFile = (index) => {
  files.value.splice(index, 1)
  pdfScanWarnings.value = [] // reset après retrait d'un fichier
  refreshFilePreviewText()
}

// Combined text preview handed to ScenarioSuggestions.  Includes every
// fetched URL's extracted text plus any client-side-readable file text.
// Kept to ~6KB on the client; the backend trims again.
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

// User picked one of the 3 scenario cards — fill the textarea but don't
// submit.  We overwrite whatever was there (including any earlier pick); if
// the user had already typed a partial scenario they can undo with Ctrl+Z.
const handleSuggestionUse = ({ question, simulationRequirement }) => {
  if (!question) return
  formData.value.simulationRequirement = simulationRequirement || question
}

// Scroll to bottom
const scrollToBottom = () => {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  })
}

// Fetch a URL and add it to urlDocs
const fetchUrlDoc = async () => {
  const url = urlInput.value.trim()
  if (!url || urlFetching.value) return

  // Prevent duplicate URLs
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

// Ask mode: ask → enrichissement web optionnel → synthesized briefing.
// Si WEB_SEARCH_MODEL est configuré côté backend, enrichAsk() est appelé
// en premier pour injecter un contexte web récent dans la question.
const askEnriching = ref(false)

const runAskMode = async () => {
  const q = askQuestion.value.trim()
  if (!q || askBusy.value) return
  askBusy.value = true
  askError.value = ''

  // Enrichissement web (US-057) — silencieux si non configuré
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
    // Don't duplicate if re-run.
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

// User picked a "What's Trending" card — push the URL into the input and
// reuse the existing fetch pipeline. ScenarioSuggestions already watches
// urlDocs and will fire once the fetched doc lands, so the user goes from
// blank-page to three scenario cards in one click.
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

// Remove a URL document from the list
const removeUrlDoc = (index) => {
  urlDocs.value.splice(index, 1)
}

const removeUrlDocByRef = (doc) => {
  const idx = urlDocs.value.indexOf(doc)
  if (idx >= 0) urlDocs.value.splice(idx, 1)
}

// Hard-cap display strings so long titles / deep URLs can't widen the
// doc-list row (CSS ellipsis can fail when intermediate flex ancestors
// don't propagate min-width:0).
const truncate = (s, max) => {
  if (!s) return ''
  return s.length > max ? s.slice(0, max - 1).trimEnd() + '…' : s
}

// Split docs by origin — Ask-synthesized briefings show under Just Ask,
// real URL fetches show under URL Import.
const askDocs = computed(() =>
  urlDocs.value.filter(d => typeof d.url === 'string' && d.url.startsWith('bassira://ask/'))
)
const fetchedDocs = computed(() =>
  urlDocs.value.filter(d => !(typeof d.url === 'string' && d.url.startsWith('bassira://ask/')))
)

// Start simulation - navigate immediately, API calls happen on the Process page
const startSimulation = () => {
  if (!canSubmit.value || loading.value) return

  // Store data pending upload
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement, urlDocs.value)

    // Navigate immediately to Process page (using special identifier for new project)
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   HOME — Hyperstitions Design System applied
   ═══════════════════════════════════════════════════════════ */

.home-container {
  min-height: 100vh;
  background: var(--wi-bg);
  font-family: var(--ms-font-body);
  color: var(--wi-on-bg);
}

/* US-094 — Trigger discret pour ouvrir SettingsPanel (admin/dev only).
   Bord bas-gauche, faible opacité au repos, opacité 1 au hover/focus.
   N'apparaît PAS dans la nav publique (cf. AppHeader). */
.home-settings-trigger {
  position: fixed;
  inset-block-end: 12px;
  inset-inline-start: 12px;
  z-index: var(--ms-z-toast, 1400);
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--wi-surface, #ffffff);
  color: var(--wi-on-surface-variant, #57423a);
  border: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.12));
  border-radius: 50%;
  font-size: 14px;
  cursor: pointer;
  opacity: 0.25;
  transition:
    opacity var(--ms-transition, 200ms),
    color var(--ms-transition, 200ms),
    background var(--ms-transition, 200ms),
    transform var(--ms-transition, 200ms);
}
.home-settings-trigger:hover,
.home-settings-trigger:focus-visible {
  opacity: 1;
  color: var(--wi-primary, #a13f0f);
  background: var(--wi-primary-soft, rgba(161, 63, 15, 0.08));
  transform: rotate(40deg);
  outline: none;
}
.home-settings-trigger:focus-visible {
  outline: 2px solid var(--wi-primary, #a13f0f);
  outline-offset: 2px;
}

/* Anciens styles `.navbar / .nav-brand / .nav-links / .nav-link /
   .nav-link--featured / .nav-link-action / .settings-btn / .compass /
   .arrow` retirés — la nav globale vit désormais dans AppHeader.vue (US-094).
   Le bouton ⚙ (admin) est remplacé par `.home-settings-trigger` plus haut. */

/* ── Main Content ── */
.main-content {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--ms-space-12) var(--ms-space-6);
}

/* ── Hero Section — Stitch « Strategic Foresight » ── */
.hero-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: var(--ms-space-12);
  padding: var(--ms-space-12) var(--ms-space-6);
  position: relative;
  background: var(--wi-bg);
  border-radius: var(--wi-radius-card);
}

/* Eyebrow pill : « بصيرة · Prospective stratégique » sur fond --wi-primary-soft */
.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  padding: 6px var(--ms-space-4);
  background: var(--wi-primary-soft);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  margin-bottom: var(--ms-space-6);
}
.hero-eyebrow-text {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-primary);
  letter-spacing: 0.01em;
}

/* Conservée pour rétro-compat — masquée tant que .tag-row n'est plus rendu */
.tag-row {
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  margin-bottom: var(--ms-space-4);
  font-family: var(--ms-font-mono);
  font-size: 13px;
}
.orange-tag {
  background: var(--ms-orange);
  color: var(--ms-text-on-color);
  padding: 4px var(--ms-space-2);
  font-weight: 700;
  letter-spacing: 3px;
  font-size: 11px;
  text-transform: uppercase;
  font-family: var(--ms-font-mono);
}

.main-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h1-size);
  line-height: var(--wi-h1-leading);
  font-weight: var(--wi-h1-weight);
  letter-spacing: var(--wi-h1-tracking);
  margin: 0 0 var(--ms-space-4) 0;
  max-width: 880px;
  color: var(--wi-on-bg);
}

.gradient-text {
  color: var(--wi-on-bg);
  -webkit-text-fill-color: var(--wi-on-bg);
  display: inline;
}

.hero-subtitle {
  font-family: var(--wi-font-body);
  font-size: 20px;
  line-height: 1.6;
  color: var(--wi-on-surface-variant);
  max-width: 640px;
  margin: 0 0 var(--ms-space-6) 0;
}

/* US-087 — Rangée de CTAs hero (primaire + secondaire) orientés modèles
   publics + commande. Empilés en colonne sur mobile (< 640 px). */
.hero-cta-row {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: var(--ms-space-3);
  margin-bottom: var(--ms-space-6);
}

/* CTA hero — base (utilisé par primary + secondary).
   Variante primaire : terracotta plein. Variante secondaire : ghost outlined. */
.hero-cta {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  border-radius: var(--wi-radius-pill);
  padding: 16px 32px;
  font-family: var(--wi-font-heading);
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: opacity var(--ms-transition), transform var(--ms-transition), box-shadow var(--ms-transition), background var(--ms-transition), color var(--ms-transition);
}

.hero-cta--primary {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: 2px solid var(--wi-primary);
  box-shadow: var(--wi-shadow-md);
}
.hero-cta--primary:hover {
  opacity: 0.92;
  background: var(--wi-primary-container);
  border-color: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  box-shadow: var(--wi-shadow-lg);
  transform: translateY(-1px);
}
.hero-cta--primary:active { transform: translateY(0); }

.hero-cta--secondary {
  background: transparent;
  color: var(--wi-primary);
  border: 2px solid var(--wi-outline-variant);
}
.hero-cta--secondary:hover {
  background: var(--wi-primary-soft);
  border-color: var(--wi-primary);
  color: var(--wi-on-primary-container);
  transform: translateY(-1px);
}
.hero-cta--secondary:active { transform: translateY(0); }

.hero-cta-arrow {
  font-family: sans-serif;
  font-size: 18px;
  line-height: 1;
}

/* Trust strip : Brier · simulations · ISO 27001 */
.hero-trust {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: var(--ms-space-4);
  background: var(--wi-surface-container-highest);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  padding: 10px var(--ms-space-6);
  margin-bottom: var(--ms-space-8);
  font-family: var(--ms-font-mono);
  font-size: 12px;
  font-weight: 500;
}
.hero-trust-item {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  white-space: nowrap;
}
.hero-trust-mint { color: var(--wi-secondary); }
.hero-trust-orange { color: var(--wi-primary-container); }
.hero-trust-icon {
  font-size: 14px;
  line-height: 1;
}
.hero-trust-sep {
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--wi-outline-variant);
}

.hero-desc {
  font-family: var(--ms-font-display);
  font-size: 18px;
  line-height: 1.6;
  color: var(--wi-on-surface-variant);
  max-width: 640px;
  margin-bottom: var(--ms-space-8);
}

.hero-desc p { margin-bottom: var(--ms-space-4); }

.highlight-bold {
  color: var(--wi-on-bg);
  font-weight: 600;
}

.highlight-orange {
  color: var(--wi-primary-container);
  font-family: var(--ms-font-mono);
  font-size: 0.85em;
}

.highlight-code {
  background: var(--wi-surface-container);
  padding: 2px var(--ms-space-1);
  font-family: var(--ms-font-mono);
  font-size: 0.85em;
  color: var(--wi-on-bg);
}

.slogan-text {
  font-family: var(--ms-font-display);
  font-size: 22px;
  line-height: 1.5;
  color: var(--wi-on-bg);
  border-inline-start: 2px solid var(--ms-orange);
  padding-inline-start: var(--ms-space-4);
  margin-top: var(--ms-space-4);
}

.blinking-cursor {
  color: var(--ms-mint);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.scroll-down-btn {
  margin-top: var(--ms-space-4);
  width: 40px;
  height: 40px;
  border: 1px solid var(--ms-border-strong);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--ms-orange);
  font-size: 1.2rem;
  border-radius: 50%;
  transition: var(--ms-transition);
}

.scroll-down-btn:hover {
  border-color: var(--ms-orange);
  background: var(--ms-orange-soft);
}

/* ── Console Intro (header « Graines de réalité ») ── */
.console-intro {
  text-align: center;
  margin: 0 auto var(--ms-space-8) auto;
  max-width: 880px;
  padding: 0 var(--ms-space-4);
}
.console-intro-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h2-size);
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-surface);
  margin: 0 0 var(--ms-space-2) 0;
}
.console-intro-subtitle {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  color: var(--wi-on-surface-variant);
  margin: 0;
}

/* ── Dashboard Section (2-column : Status & Console) ── */
.dashboard-section {
  display: flex;
  gap: var(--ms-space-8);
  padding-top: 0;
  align-items: flex-start;
}

.dashboard-section .left-panel,
.dashboard-section .right-panel {
  display: flex;
  flex-direction: column;
}

/* ── Left Panel — carte « Statut » ── */
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

.status-dot {
  color: var(--wi-secondary);
  font-size: 0.8rem;
}

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

/* ── Metric Cards (legacy — non rendues mais conservées en CSS) ── */
.metrics-row {
  display: flex;
  gap: var(--ms-space-4);
  margin-bottom: var(--ms-space-4);
}

.metric-card {
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  padding: var(--ms-space-4) var(--ms-space-6);
  min-width: 150px;
  transition: var(--ms-transition-fast);
}
.metric-card:hover { border-color: var(--ms-orange); }
.metric-value {
  font-family: var(--ms-font-display);
  font-size: 28px;
  margin-bottom: var(--ms-space-1);
}
.metric-label {
  font-family: var(--ms-font-mono);
  font-size: 13px;
  color: var(--ms-text-muted);
  letter-spacing: 0.06em;
}

/* ── Workflow Steps — carte douce sans corners terminal ── */
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

.diamond-icon {
  color: var(--wi-primary-container);
  font-size: 1rem;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-4);
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ms-space-4);
}

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

/* ── Right Console — carte « Upload » Stitch ── */
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

.console-label {
  font-weight: 600;
  letter-spacing: 0.12em;
}
.console-meta {
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  text-transform: none;
  letter-spacing: 0;
}

/* ── Upload Zone (drag-drop "Glissez vos documents ici") ── */
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

/* ── File List ── */
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

/* ── Console Divider ── */
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

/* ── Text Input ── */
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

.code-input::placeholder {
  color: var(--ms-text-subtle);
}

.model-badge {
  position: absolute;
  bottom: var(--ms-space-1);
  inset-inline-end: var(--ms-space-2);
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--ms-text-subtle);
  letter-spacing: 0.06em;
}

/* ── Launch Button (CTA primaire warm orange) ── */
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

.start-engine-btn:active:not(:disabled) {
  opacity: 0.92;
}

.start-engine-btn:disabled {
  background: var(--ms-bg-muted);
  color: var(--ms-text-subtle);
  cursor: not-allowed;
  border-color: var(--ms-border);
  box-shadow: none;
}

/* ── URL Import Section / Just Ask ── */
.url-section {
  padding-top: 0;
}

.url-input-row {
  display: flex;
  gap: var(--ms-space-2);
}

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

.url-input::placeholder {
  color: var(--ms-text-subtle);
}

.url-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

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

.url-fetch-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

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

.url-doc-info {
  flex: 1;
  min-width: 0;
}

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

/* ── Footer (legacy — non rendu) ── */
.attribution-footer {
  text-align: center;
  padding: var(--ms-space-6) 0;
  font-family: var(--ms-font-mono);
  font-size: 13px;
  color: var(--ms-text-subtle);
  letter-spacing: 0.06em;
}

.attribution-footer a {
  color: var(--ms-text-muted);
  text-decoration: none;
}

.attribution-footer a:hover {
  color: var(--ms-orange);
}

/* ── Doc Preview Modal ── */
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

/* ── Responsive ── */
@media (max-width: 1024px) {
  .dashboard-section { flex-direction: column; }
  .main-title { font-size: 36px; }
  .hero-subtitle { font-size: 17px; }
  .hero-cta { font-size: 16px; padding: 14px 28px; }
}

@media (max-width: 640px) {
  .main-title { font-size: 32px; }
  .hero-trust { font-size: 11px; gap: var(--ms-space-2); padding: 8px var(--ms-space-3); }
  .hero-section { padding: var(--ms-space-8) var(--ms-space-3); }
}

/* ── PDF scan warning ── */
.pdf-scan-warning {
  display: flex; gap: var(--ms-space-2); align-items: flex-start;
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
