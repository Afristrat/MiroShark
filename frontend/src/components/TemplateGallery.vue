<template>
  <div class="template-gallery">
    <div class="gallery-header">
      <div class="header-left">
        <span class="header-icon">◈</span>
        <span class="header-label">{{ $t('templates.gallery.title') }}</span>
      </div>
      <span class="header-meta">{{ $t('templates.gallery.ready', { count: templates.length }) }}</span>
    </div>

    <div v-if="loading" class="gallery-loading">
      {{ $t('templates.gallery.loading') }}
    </div>

    <div v-else-if="templates.length === 0" class="gallery-empty">
      {{ $t('templates.gallery.empty') }}
    </div>

    <div v-else class="template-grid">
      <div
        v-for="template in templates"
        :key="template.id"
        class="template-card"
        :class="{ selected: selectedId === template.id, loading: launchingId === template.id }"
        @click="selectTemplate(template)"
      >
        <div class="card-top">
          <span class="card-icon">{{ iconMap[template.icon] || '◆' }}</span>
          <span class="card-category">{{ template.category }}</span>
        </div>

        <h3 class="card-title">{{ template.name }}</h3>
        <p class="card-desc">{{ template.description }}</p>

        <div class="card-meta">
          <span class="meta-item" :title="$t('templates.gallery.agentsTitle', { count: template.estimated_agents })">
            {{ $t('templates.gallery.agents', { count: template.estimated_agents }) }}
          </span>
          <span class="meta-dot">·</span>
          <span class="meta-item" :title="$t('templates.gallery.roundsTitle', { count: template.estimated_rounds })">
            {{ $t('templates.gallery.rounds', { count: template.estimated_rounds }) }}
          </span>
          <span class="meta-dot">·</span>
          <span class="meta-item difficulty" :class="template.difficulty">
            {{ difficultyText(template.difficulty) }}
          </span>
        </div>

        <div class="card-platforms">
          <span v-for="p in template.platforms" :key="p" class="platform-badge">{{ p }}</span>
          <span
            v-if="template.has_counterfactuals"
            class="platform-badge platform-badge--cf"
            :title="$t('templates.gallery.branchesTitle', { count: template.counterfactual_count })"
          >
            {{ $t('templates.gallery.branches', { count: template.counterfactual_count }) }}
          </span>
          <span
            v-if="template.has_oracle_tools"
            class="platform-badge platform-badge--oracle"
            :title="$t('templates.gallery.oracleTitle', { count: template.oracle_tool_count })"
          >
            {{ $t('templates.gallery.oracleData') }}
          </span>
        </div>

        <label
          v-if="template.has_oracle_tools"
          class="oracle-toggle"
          :class="{ disabled: !capabilities.oracle_seed_enabled }"
          :title="capabilities.oracle_seed_enabled
            ? $t('templates.gallery.oracleEnabled')
            : $t('templates.gallery.oracleDisabled')"
          @click.stop
        >
          <input
            type="checkbox"
            :checked="oracleOptIn[template.id] || false"
            :disabled="!capabilities.oracle_seed_enabled"
            @change="toggleOracleOpt(template.id, $event.target.checked)"
          />
          <span>{{ $t('templates.gallery.useLiveOracle') }}</span>
        </label>

        <!-- US-019 — Templates avec variants A/B/C : 3 sub-actions au lieu
             d'un bouton Launch unique. Couvre `she_start_cohort_replay`
             (Replay / Twin / Blind Spot). Les libellés courts sont en
             i18n (templates.sheStart.* pour She Start, fallback générique
             "Variant A/B/C" pour les futurs templates à variants). -->
        <div v-if="template.has_variants" class="variant-row">
          <button
            v-for="letter in ['A', 'B', 'C']"
            :key="letter"
            class="variant-btn"
            :class="{ loading: launchingVariantKey === template.id + ':' + letter }"
            :disabled="!!launchingVariantKey"
            :title="variantTitle(template.id, letter)"
            @click.stop="launchTemplate(template, letter)"
          >
            <span class="variant-letter">{{ letter }}</span>
            <span class="variant-label">{{ variantLabel(template.id, letter) }}</span>
          </button>
        </div>
        <button
          v-else
          class="launch-btn"
          :disabled="launchingId === template.id"
          @click.stop="launchTemplate(template)"
        >
          <span v-if="launchingId === template.id">{{ $t('templates.gallery.launchLoading') }}</span>
          <span v-else-if="oracleOptIn[template.id] && capabilities.oracle_seed_enabled">{{ $t('templates.gallery.launchLive') }}</span>
          <span v-else>{{ $t('templates.gallery.launch') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { listTemplates, getTemplate, getTemplateCapabilities } from '../api/templates'
import { setPendingTemplate } from '../store/pendingUpload'

const router = useRouter()
const { t } = useI18n()

// Translate the difficulty enum returned by the API. Falls back to the raw
// value if it doesn't match one of our known keys.
const difficultyText = (level) => {
  const key = level === 'easy' ? 'templates.difficulty.easy'
    : level === 'medium' ? 'templates.difficulty.medium'
    : level === 'hard' ? 'templates.difficulty.hard'
    : null
  return key ? t(key) : level
}

const templates = ref([])
const loading = ref(true)
const selectedId = ref(null)
const launchingId = ref(null)
const launchingVariantKey = ref(null)  // US-019 — clé `${templateId}:${letter}`
const capabilities = ref({ oracle_seed_enabled: false, mcp_agent_tools_enabled: false })
const oracleOptIn = reactive({})  // templateId → bool (opt-in per card)

// US-019 — libellés courts par template+letter pour la version She Start.
// Fallback générique « Variant A/B/C » pour tout autre template à variants.
const variantLabel = (templateId, letter) => {
  if (templateId === 'she_start_cohort_replay') {
    if (letter === 'A') return t('templates.sheStart.variantA')
    if (letter === 'B') return t('templates.sheStart.variantB')
    if (letter === 'C') return t('templates.sheStart.variantC')
  }
  return t('templates.gallery.variantGeneric', { letter })
}
const variantTitle = (templateId, letter) => {
  if (templateId === 'she_start_cohort_replay') {
    if (letter === 'A') return t('templates.sheStart.variantATitle')
    if (letter === 'B') return t('templates.sheStart.variantBTitle')
    if (letter === 'C') return t('templates.sheStart.variantCTitle')
  }
  return t('templates.gallery.variantGenericTitle', { letter })
}

const toggleOracleOpt = (templateId, checked) => {
  oracleOptIn[templateId] = checked
}

const iconMap = {
  vote: '🗳',
  chart: '📈',
  alert: '⚠',
  rocket: '🚀',
  clock: '⏳',
  school: '🎓'
}

// Retry the initial fetch a few times. The frontend (Vite) is up before
// the backend has finished warming up — a single attempt often returns
// nothing on first page load, leaving the gallery empty until the user
// refreshes. Backoff: 0ms, 750ms, 1500ms, 3000ms.
const fetchWithRetry = async () => {
  const delays = [0, 750, 1500, 3000]
  for (let i = 0; i < delays.length; i++) {
    if (delays[i]) await new Promise(r => setTimeout(r, delays[i]))
    try {
      const [listRes, capsRes] = await Promise.all([
        listTemplates(),
        getTemplateCapabilities().catch(() => null),
      ])
      if (capsRes?.success) capabilities.value = capsRes.data
      if (listRes?.success && Array.isArray(listRes.data) && listRes.data.length > 0) {
        templates.value = listRes.data
        return
      }
    } catch (e) {
      if (i === delays.length - 1) console.error('Failed to load templates:', e)
    }
  }
}

onMounted(async () => {
  try {
    await fetchWithRetry()
  } finally {
    loading.value = false
  }
})

const selectTemplate = (template) => {
  selectedId.value = selectedId.value === template.id ? null : template.id
}

const launchTemplate = async (template, variantLetter = null) => {
  // US-019 — variantLetter est 'A' | 'B' | 'C' pour les templates à variants
  // (she_start_cohort_replay actuellement). Si null → comportement legacy
  // mono-launch.
  if (variantLetter) {
    launchingVariantKey.value = `${template.id}:${variantLetter}`
  } else {
    launchingId.value = template.id
  }

  try {
    const enrich = !!(oracleOptIn[template.id] && capabilities.value.oracle_seed_enabled)
    const res = await getTemplate(template.id, { enrich })
    if (!res?.success) return

    const full = res.data
    let requirement = full.simulation_requirement
    let seed = full.seed_document
    let name = full.name

    // US-019 — sélection variant : on retrouve l'objet variant dans la liste
    // par son letter ('A'/'B'/'C') et on enrichit le requirement avec ses
    // paramètres spécifiques (runs, rounds, agents, leaders_removed). Ainsi
    // au moment de la préparation côté Step1/Step2, le LLM voit le contexte
    // du variant choisi et adapte ontologie + profils en conséquence.
    if (variantLetter && Array.isArray(full.variants)) {
      const variant = full.variants.find(v => v.letter === variantLetter)
      if (variant) {
        const paramsBlock = `\n\n--- Variant choisi : ${variant.name} ---\n` +
          `Objectif : ${variant.objective || '—'}\n` +
          `Configuration : ${variant.runs || 1} run(s) × ${variant.rounds || full.estimated_rounds || '?'} rounds, ` +
          `${(variant.agents && variant.agents.total) || full.estimated_agents || '?'} agents.\n` +
          `Question marché : ${variant.market_question || full.default_market_question || ''}\n` +
          (variant.leaders_removed && variant.leaders_removed.length
            ? `Leaders retirés : ${variant.leaders_removed.join(' ; ')}\n`
            : '') +
          `Sortie attendue : ${variant.expected_outcome || ''}\n`
        requirement = (requirement || '') + paramsBlock
        name = `${full.name} — ${variant.name}`
      }
    }

    setPendingTemplate(requirement, seed, name)
    router.push({ name: 'Process', params: { projectId: 'new' } })
  } catch (e) {
    console.error('Failed to load template:', e)
  } finally {
    launchingId.value = null
    launchingVariantKey.value = null
  }
}
</script>

<style scoped>
/* ─── Warm Intelligence refresh (US-053) ───
   TemplateGallery sur la palette --wi-* :
   - container surface cream sans bordure rigide,
   - grille 3 colonnes desktop avec cards radius-card et lift hover,
   - category badges teintés alternativement (warm progressive),
   - CTA Launch terracotta plein. */
.template-gallery {
  background: var(--wi-bg);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-lg);
  margin-top: var(--wi-space-xl);
  box-shadow: var(--wi-shadow-sm);
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: var(--wi-space-md);
  gap: var(--wi-space-md);
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  color: var(--wi-on-bg);
}

.header-icon {
  font-size: 1.2rem;
  color: var(--wi-primary-container);
}

.header-meta {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 500;
  color: var(--wi-on-surface-variant);
  letter-spacing: 0;
}

.gallery-loading,
.gallery-empty {
  text-align: center;
  padding: var(--wi-space-lg);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  background: var(--wi-surface-container-low);
  border-radius: var(--wi-radius-interactive);
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--wi-space-md);
}

.template-card {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  cursor: pointer;
  transition: transform var(--ms-transition),
              box-shadow var(--ms-transition),
              border-color var(--ms-transition);
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: var(--wi-shadow-ambient);
}

.template-card:hover {
  transform: translateY(-4px);
  border-color: var(--wi-primary-container);
  box-shadow: var(--wi-shadow-orange);
}

.template-card.selected {
  border-color: var(--wi-primary-container);
  box-shadow: var(--wi-shadow-orange);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--wi-space-sm);
}

.card-icon {
  font-size: 1.6rem;
  line-height: 1;
}

/* Category badge — alternance via :nth-child du parent .template-card.
   Note : le sélecteur .template-card ne sait pas distinguer les types
   sémantiques. On garde un look unifié warm cream + accent terracotta.  */
.card-category {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  color: var(--wi-on-primary-container);
  background: var(--wi-primary-container);
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  text-transform: none;
  letter-spacing: 0;
}

.card-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-text-lg, 17px);
  font-weight: 600;
  margin: 0 0 8px 0;
  line-height: 1.3;
  color: var(--wi-on-surface);
}

.card-desc {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  line-height: var(--wi-body-md-leading);
  margin: 0 0 var(--wi-space-sm) 0;
  flex: 1;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: var(--wi-space-xs);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}

.meta-dot {
  color: var(--wi-outline-variant);
}

/* Difficulty mapping warm — vert / peach / rose terracotta */
.difficulty.easy   { color: var(--wi-secondary); font-weight: 600; }
.difficulty.medium { color: var(--ms-peach); font-weight: 600; }
.difficulty.hard   { color: var(--wi-on-primary-container); font-weight: 600; }

.card-platforms {
  display: flex;
  gap: 6px;
  margin-bottom: var(--wi-space-sm);
  flex-wrap: wrap;
  row-gap: 6px;
}

.platform-badge {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 500;
  padding: 4px 10px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  background: var(--wi-surface-container-low);
  color: var(--wi-on-surface-variant);
  text-transform: lowercase;
  white-space: nowrap;
}

.platform-badge--cf {
  border-color: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  background: var(--wi-surface-container);
}

.platform-badge--oracle {
  border-color: var(--wi-secondary);
  color: var(--wi-on-secondary-container);
  background: var(--wi-secondary-container);
}

.oracle-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-on-secondary-container);
  margin-bottom: var(--wi-space-xs);
  cursor: pointer;
  user-select: none;
}

.oracle-toggle input[type="checkbox"] {
  accent-color: var(--wi-secondary);
  cursor: pointer;
}

.oracle-toggle.disabled {
  color: var(--wi-outline);
  cursor: not-allowed;
}

.oracle-toggle.disabled input[type="checkbox"] {
  cursor: not-allowed;
}

.launch-btn {
  width: 100%;
  padding: 12px;
  background: var(--wi-on-primary-container);
  color: var(--wi-on-primary);
  border: 1px solid var(--wi-on-primary-container);
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-heading);
  font-size: var(--wi-label-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--ms-transition),
              transform var(--ms-transition),
              box-shadow var(--ms-transition);
  letter-spacing: var(--wi-label-sm-tracking);
}

.launch-btn:hover:not(:disabled) {
  background: var(--wi-primary);
  border-color: var(--wi-primary);
  transform: translateY(-1px);
  box-shadow: var(--wi-shadow-md);
}

.launch-btn:disabled {
  background: var(--wi-surface-container-high);
  color: var(--wi-outline);
  border-color: var(--wi-outline-variant);
  cursor: not-allowed;
}

/* US-019 — variant row : 3 sub-actions Replay/Twin/Blind Spot pour
   les templates à variants (she_start_cohort_replay). */
.variant-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-block-start: auto;
}

.variant-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 12px 8px;
  background: var(--wi-surface-container-low);
  color: var(--wi-on-primary-container);
  border: 1px solid var(--wi-primary-container);
  border-radius: var(--wi-radius-interactive);
  cursor: pointer;
  font-family: var(--wi-font-heading);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: var(--wi-label-sm-tracking);
  line-height: 1.2;
  transition: background var(--ms-transition),
              color var(--ms-transition),
              transform var(--ms-transition),
              box-shadow var(--ms-transition);
  min-height: 56px;
}

.variant-btn:hover:not(:disabled) {
  background: var(--wi-on-primary-container);
  color: var(--wi-on-primary);
  border-color: var(--wi-on-primary-container);
  transform: translateY(-1px);
  box-shadow: var(--wi-shadow-md);
}

.variant-btn.variant-btn:disabled,
.variant-btn[disabled] {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.variant-btn.loading {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
}

.variant-letter {
  font-family: var(--ms-font-mono);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  opacity: 0.7;
}

.variant-label {
  font-size: var(--wi-caption);
  text-transform: none;
}

@media (max-width: 1024px) {
  .template-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .template-grid {
    grid-template-columns: 1fr;
  }
}
</style>
