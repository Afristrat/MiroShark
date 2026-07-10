<template>
  <div class="aap-page">
    <header class="aap-topbar">
      <router-link to="/" class="aap-back" :title="$t('nav.homeTitle') || 'Accueil'">
        <span aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') || 'BASSIRA' }}</span>
      </router-link>
    </header>

    <main class="aap-main">
      <section class="aap-hero">
        <h1>{{ $t('adminAgentPlaybook.title') || 'Playbook agent Intake' }}</h1>
        <p class="aap-sub">
          {{ $t('adminAgentPlaybook.subtitle') || 'Escalades silencieuses et corrections vivantes de l\'agent de qualification (ADR-IQ-08).' }}
        </p>
      </section>

      <!-- Escalades -->
      <section class="aap-section">
        <h2>{{ $t('adminAgentPlaybook.escalationsTitle') || 'Escalades' }}</h2>
        <label class="aap-checkbox">
          <input type="checkbox" v-model="unreviewedOnly" @change="loadEscalations" />
          {{ $t('adminAgentPlaybook.unreviewedOnly') || 'Non revues uniquement' }}
        </label>
        <p v-if="escalationsLoading" class="aap-state">{{ $t('adminAgentPlaybook.loading') || 'Chargement…' }}</p>
        <p v-else-if="escalations.length === 0" class="aap-state">{{ $t('adminAgentPlaybook.noEscalations') || 'Aucune escalade.' }}</p>
        <ul v-else class="aap-list">
          <li v-for="e in escalations" :key="e.id" class="aap-card">
            <div class="aap-card-head">
              <span class="aap-badge">{{ e.category }}</span>
              <span v-if="e.reviewed_at" class="aap-badge aap-badge--ok">{{ $t('adminAgentPlaybook.reviewed') || 'Revue' }}</span>
            </div>
            <p><strong>{{ $t('adminAgentPlaybook.userMessage') || 'Prospect' }} :</strong> {{ e.user_message }}</p>
            <p><strong>{{ $t('adminAgentPlaybook.agentMessage') || 'Agent' }} :</strong> {{ e.agent_message }}</p>
            <div v-if="!e.reviewed_at" class="aap-review-form">
              <textarea v-model="reviewNotes[e.id]" :placeholder="$t('adminAgentPlaybook.notePlaceholder') || 'Note (optionnelle)'"></textarea>
              <button type="button" class="aap-btn" @click="reviewEscalation(e.id)">
                {{ $t('adminAgentPlaybook.markReviewed') || 'Marquer revue' }}
              </button>
            </div>
          </li>
        </ul>
      </section>

      <!-- Playbook -->
      <section class="aap-section">
        <h2>{{ $t('adminAgentPlaybook.playbookTitle') || 'Corrections (playbook)' }}</h2>
        <form class="aap-form" @submit.prevent="submitNewEntry">
          <label>
            {{ $t('adminAgentPlaybook.situationLabel') || 'Situation rencontrée' }}
            <textarea v-model="newEntry.situation_pattern" required></textarea>
          </label>
          <label>
            {{ $t('adminAgentPlaybook.correctedLabel') || 'Réponse attendue' }}
            <textarea v-model="newEntry.corrected_response" required></textarea>
          </label>
          <button type="submit" class="aap-btn aap-btn--primary" :disabled="submitting">
            {{ $t('adminAgentPlaybook.addEntry') || 'Ajouter au playbook' }}
          </button>
        </form>

        <p v-if="playbookLoading" class="aap-state">{{ $t('adminAgentPlaybook.loading') || 'Chargement…' }}</p>
        <ul v-else class="aap-list">
          <li v-for="p in playbookEntries" :key="p.id" class="aap-card">
            <p><strong>{{ $t('adminAgentPlaybook.situationLabel') || 'Situation' }} :</strong> {{ p.situation_pattern }}</p>
            <p><strong>{{ $t('adminAgentPlaybook.correctedLabel') || 'Réponse' }} :</strong> {{ p.corrected_response }}</p>
            <button type="button" class="aap-btn aap-btn--ghost" @click="toggleEntry(p)">
              {{ p.active
                ? ($t('adminAgentPlaybook.deactivate') || 'Désactiver')
                : ($t('adminAgentPlaybook.activate') || 'Activer') }}
            </button>
          </li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  fetchIntakeEscalations,
  reviewIntakeEscalation,
  fetchIntakePlaybook,
  createIntakePlaybookEntry,
  toggleIntakePlaybookEntry,
} from '../api/client'

const escalations = ref([])
const escalationsLoading = ref(false)
const unreviewedOnly = ref(true)
const reviewNotes = reactive({})

const playbookEntries = ref([])
const playbookLoading = ref(false)
const newEntry = reactive({ situation_pattern: '', corrected_response: '' })
const submitting = ref(false)

async function loadEscalations() {
  escalationsLoading.value = true
  try {
    const res = await fetchIntakeEscalations({ unreviewed_only: unreviewedOnly.value })
    escalations.value = res?.data?.escalations || []
  } finally {
    escalationsLoading.value = false
  }
}

async function reviewEscalation(id) {
  await reviewIntakeEscalation(id, { reviewer_note: reviewNotes[id] || null })
  await loadEscalations()
}

async function loadPlaybook() {
  playbookLoading.value = true
  try {
    const res = await fetchIntakePlaybook()
    playbookEntries.value = res?.data?.entries || []
  } finally {
    playbookLoading.value = false
  }
}

async function submitNewEntry() {
  submitting.value = true
  try {
    await createIntakePlaybookEntry({ ...newEntry })
    newEntry.situation_pattern = ''
    newEntry.corrected_response = ''
    await loadPlaybook()
  } finally {
    submitting.value = false
  }
}

async function toggleEntry(entry) {
  await toggleIntakePlaybookEntry(entry.id, !entry.active)
  await loadPlaybook()
}

onMounted(() => {
  loadEscalations()
  loadPlaybook()
})
</script>

<style scoped>
.aap-page { min-height: 100vh; background: var(--wi-surface, #ffffff); color: var(--wi-on-surface, #241915); }
.aap-topbar { display: flex; align-items: center; padding: 16px 24px; }
.aap-back { display: flex; gap: 8px; text-decoration: none; color: inherit; font-weight: 600; }
.aap-main { max-width: 780px; margin: 0 auto; padding: 0 24px 64px; }
.aap-hero h1 { font-size: 1.6rem; margin-bottom: 4px; }
.aap-sub { color: var(--wi-on-surface-variant, #57423a); }
.aap-section { margin-top: 40px; }
.aap-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.aap-card { background: var(--wi-surface-container-low, #fff1ec); border: 1px solid var(--wi-outline-variant, #dec0b6); border-radius: 10px; padding: 14px 16px; }
.aap-card-head { display: flex; gap: 8px; margin-bottom: 8px; }
.aap-badge { font-size: 0.7rem; text-transform: uppercase; padding: 2px 8px; border-radius: 999px; background: var(--wi-surface, #ffffff); border: 1px solid var(--wi-outline-variant, #dec0b6); }
.aap-badge--ok { background: #eaf3ea; color: #2f6b3a; }
.aap-review-form, .aap-form { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.aap-form label { display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; }
.aap-btn { align-self: flex-start; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--wi-outline-variant, #dec0b6); background: var(--wi-surface, #ffffff); cursor: pointer; }
.aap-btn--primary { background: var(--wi-primary-container, #ff8551); color: white; border-color: transparent; }
.aap-state { color: var(--wi-on-surface-variant, #57423a); }
.aap-checkbox { display: flex; align-items: center; gap: 6px; margin-bottom: 12px; font-size: 0.9rem; }
</style>
