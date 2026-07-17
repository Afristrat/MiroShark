<template>
  <Teleport to="body">
    <div v-if="open" class="settings-overlay" @click.self="$emit('close')">
      <div class="settings-modal">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-title">
            <span class="title-label">⚙ {{ $t('panels.settings.title') }}</span>
          </div>
          <button class="close-btn" @click="$emit('close')" :aria-label="$t('panels.settings.close')">✕</button>
        </div>

        <div class="warning-stripe"></div>

        <!-- Current Setup Summary -->
        <section class="settings-section">
          <div class="section-header">
            <span class="section-label">{{ $t('settings.status.title') }}</span>
            <div class="status-badge" :class="testStatus">
              <span class="badge-dot"></span>
              {{ testStatusText }}
            </div>
          </div>

          <div class="setup-grid">
            <div class="setup-row">
              <span class="setup-key">{{ $t('settings.status.defaultModel') }}</span>
              <span class="setup-val">{{ currentSettings.llm?.model_name || '—' }}</span>
            </div>
            <div class="setup-row">
              <span class="setup-key">{{ $t('settings.status.smartModel') }}</span>
              <span class="setup-val">{{ currentSettings.smart?.model_name || inheritMarker }}</span>
            </div>
            <div class="setup-row">
              <span class="setup-key">{{ $t('settings.status.nerModel') }}</span>
              <span class="setup-val">{{ currentSettings.ner?.model_name || inheritMarker }}</span>
            </div>
            <div class="setup-row">
              <span class="setup-key">{{ $t('settings.status.wonderwallModel') }}</span>
              <span class="setup-val">{{ currentSettings.wonderwall?.model_name || inheritMarker }}</span>
            </div>
            <div class="setup-row">
              <span class="setup-key">{{ $t('settings.status.embeddings') }}</span>
              <span class="setup-val">
                {{ currentSettings.embedding?.model_name || '—' }}
              </span>
            </div>
            <div class="setup-row">
              <span class="setup-key">{{ $t('settings.status.webSearch') }}</span>
              <span class="setup-val">{{ currentSettings.web_search_model || inheritMarker }}</span>
            </div>
            <div class="setup-row">
              <span class="setup-key">{{ $t('settings.status.apiKey') }}</span>
              <span class="setup-val">
                <span v-if="currentSettings.llm?.has_api_key">
                  {{ currentSettings.llm.api_key_masked }}
                </span>
                <span v-else class="setup-missing">{{ $t('settings.status.notSet') }}</span>
              </span>
            </div>
          </div>
        </section>

        <!-- Preset Picker -->
        <section class="settings-section">
          <div class="section-header">
            <span class="section-label">{{ $t('settings.preset.title') }}</span>
          </div>

          <div class="field-row">
            <label class="field-label">{{ $t('settings.preset.label') }}</label>
            <div class="select-wrapper">
              <select v-model="form.preset" class="field-select ms-input">
                <option value="">{{ $t('settings.preset.custom') }}</option>
                <option
                  v-for="p in presetOptions"
                  :key="p.id"
                  :value="p.id"
                >
{{ p.label }}
</option>
              </select>
            </div>
            <div class="field-hint">
              Applies the full set of model slots on save. See
              <a href="https://github.com/aaronjmars/MiroShark/blob/main/.env.example"
                 target="_blank" rel="noopener">.env.example</a>
              for the exact values each preset uses.
            </div>
          </div>

          <div v-if="presetNeedsKey" class="field-row">
            <label class="field-label">{{ $t('settings.preset.keyLabel') }}</label>
            <div class="key-input-group">
              <input
                v-model="form.presetApiKey"
                class="field-input ms-input"
                :type="showKey ? 'text' : 'password'"
                placeholder="sk-or-v1-..."
              />
              <button class="toggle-key-btn" @click="showKey = !showKey">
                {{ showKey ? '◉' : '◎' }}
              </button>
            </div>
            <div class="field-hint">
              Filled into every slot the preset needs (default, smart, NER, embedding).
              Leave blank to keep your existing keys.
            </div>
          </div>
        </section>

        <!-- LLM Configuration — BYOK wizard -->
        <section class="settings-section byok-section">
          <div class="section-header">
            <span class="section-label">{{ $t('settings.byok.title') }}</span>
            <div v-if="detectedProvider" class="provider-badge provider-badge--detected">
              <span class="provider-badge-dot">✓</span>
              {{ detectedProvider.name }} {{ $t('settings.byok.detected') }}
            </div>
            <div v-else-if="form.llm.api_key && form.llm.api_key.length > 4" class="provider-badge provider-badge--custom">
              {{ $t('settings.byok.customProvider') }}
            </div>
          </div>

          <p class="byok-intro">{{ $t('settings.byok.intro') }}</p>

          <!-- Clé API — champ principal -->
          <div class="field-row byok-key-row">
            <label class="field-label">{{ $t('settings.byok.keyLabel') }}</label>
            <div class="key-input-group">
              <input
                v-model="form.llm.api_key"
                class="field-input ms-input byok-key-input"
                :type="showKey ? 'text' : 'password'"
                :placeholder="currentSettings.llm?.api_key_masked || $t('settings.byok.keyPlaceholder')"
                autocomplete="off"
                spellcheck="false"
              />
              <button class="toggle-key-btn" @click="showKey = !showKey" :title="showKey ? $t('settings.byok.hideKey') : $t('settings.byok.showKey')">
                {{ showKey ? '◉' : '◎' }}
              </button>
            </div>
            <div v-if="detectedProvider" class="field-hint byok-hint-detected">
              🔗 {{ $t('settings.byok.autoBaseUrl') }} <code>{{ detectedProvider.url }}</code>
            </div>
            <div v-if="currentSettings.llm?.has_api_key && !form.llm.api_key" class="field-hint">
              {{ $t('settings.byok.currentKey') }}: {{ currentSettings.llm.api_key_masked }} — {{ $t('settings.byok.keepBlank') }}
            </div>
          </div>

          <!-- Modèle — sélecteur intelligent -->
          <div class="field-row">
            <label class="field-label">{{ $t('settings.byok.modelLabel') }}</label>
            <div class="model-input-group">
              <div class="select-wrapper model-select-wrapper">
                <!-- Modèles curatés si provider détecté -->
                <select
                  v-if="curatedModelList.length > 0"
                  v-model="form.llm.model_name"
                  class="field-select ms-input"
                >
                  <option
                    v-for="m in curatedModelList"
                    :key="m.id"
                    :value="m.id"
                  >
{{ m.name }} — {{ m.desc }}
</option>
                  <option value="__custom">{{ $t('settings.byok.customModel') }}…</option>
                </select>
                <!-- Champ libre si pas de liste curatée -->
                <input
                  v-else
                  v-model="form.llm.model_name"
                  class="field-input ms-input"
                  type="text"
                  :placeholder="$t('settings.byok.modelPlaceholder')"
                />
              </div>
              <!-- Bouton charge modèles OpenRouter uniquement -->
              <button
                v-if="isOpenRouter"
                class="load-models-btn"
                :disabled="loadingModels"
                @click="loadOpenRouterModels"
                :title="$t('settings.byok.loadModelsTitle')"
              >
                <span v-if="loadingModels">...</span>
                <span v-else>↻</span>
              </button>
            </div>
            <div v-if="modelLoadError" class="field-error">{{ modelLoadError }}</div>
          </div>

          <!-- Champ modèle custom si option __custom sélectionnée -->
          <div v-if="form.llm.model_name === '__custom'" class="field-row">
            <label class="field-label">{{ $t('settings.byok.customModelLabel') }}</label>
            <input
              v-model="customModelInput"
              class="field-input ms-input"
              type="text"
              :placeholder="$t('settings.byok.customModelPlaceholder')"
              @change="form.llm.model_name = customModelInput"
            />
          </div>

          <!-- Base URL — collapsible (pré-remplie par détection) -->
          <details class="byok-advanced" :open="!detectedProvider">
            <summary class="byok-advanced-toggle">{{ $t('settings.byok.advancedUrl') }}</summary>
            <div class="field-row byok-url-row">
              <label class="field-label">Base URL</label>
              <input
                v-model="form.llm.base_url"
                class="field-input ms-input"
                type="url"
                :placeholder="detectedProvider ? detectedProvider.url : 'https://openrouter.ai/api/v1'"
              />
            </div>
          </details>

          <!-- Test de connexion -->
          <div class="field-row test-row">
            <button class="test-btn" :disabled="testing" @click="testConnection">
              <span v-if="testing">{{ $t('settings.byok.testing') }}</span>
              <span v-else>{{ $t('settings.byok.testBtn') }}</span>
            </button>
            <div v-if="testResult" class="test-result" :class="testResult.success ? 'ok' : 'fail'">
              <span v-if="testResult.success">✓ {{ testResult.model }} — {{ testResult.latency_ms }}ms</span>
              <span v-else>✗ {{ testResult.error }}</span>
            </div>
          </div>

          <!-- Propagation intelligente -->
          <div class="byok-propagation-hint">
            <span class="byok-prop-icon">💡</span>
            {{ $t('settings.byok.propagationHint') }}
          </div>
        </section>

        <!-- Advanced: per-slot overrides -->
        <section class="settings-section">
          <button class="advanced-toggle" @click="advancedOpen = !advancedOpen">
            <span class="section-label">
              {{ $t('settings.advanced.title') }}
            </span>
            <span class="chevron">{{ advancedOpen ? '−' : '+' }}</span>
          </button>

          <div v-if="advancedOpen" class="advanced-body">
            <div class="advanced-hint">
              {{ $t('settings.advanced.hint') }}
            </div>

            <!-- Smart -->
            <div class="advanced-group">
              <div class="advanced-group-title">{{ $t('settings.advanced.smart') }}</div>
              <div class="field-row">
                <label class="field-label">Model</label>
                <input
                  v-model="form.smart.model_name"
                  class="field-input ms-input"
                  type="text"
                  placeholder="e.g. anthropic/claude-sonnet-4.6"
                />
              </div>
            </div>

            <!-- NER -->
            <div class="advanced-group">
              <div class="advanced-group-title">{{ $t('settings.advanced.ner') }}</div>
              <div class="field-row">
                <label class="field-label">Model</label>
                <input
                  v-model="form.ner.model_name"
                  class="field-input ms-input"
                  type="text"
                  placeholder="e.g. google/gemini-2.0-flash-001"
                />
              </div>
            </div>

            <!-- Wonderwall -->
            <div class="advanced-group">
              <div class="advanced-group-title">{{ $t('settings.advanced.wonderwall') }}</div>
              <div class="field-row">
                <label class="field-label">Model</label>
                <input
                  v-model="form.wonderwall.model_name"
                  class="field-input ms-input"
                  type="text"
                  placeholder="e.g. google/gemini-2.0-flash-lite-001"
                />
              </div>
            </div>

            <!-- Embedding -->
            <div class="advanced-group">
              <div class="advanced-group-title">{{ $t('settings.advanced.embeddings') }}</div>
              <div class="field-row">
                <label class="field-label">Provider</label>
                <div class="select-wrapper">
                  <select v-model="form.embedding.provider" class="field-select ms-input">
                    <option value="ollama">Ollama (local)</option>
                    <option value="openai">OpenAI-compatible</option>
                  </select>
                </div>
              </div>
              <div class="field-row">
                <label class="field-label">Model</label>
                <input
                  v-model="form.embedding.model_name"
                  class="field-input ms-input"
                  type="text"
                  placeholder="e.g. openai/text-embedding-3-small"
                />
              </div>
            </div>

            <!-- Web Search -->
            <div class="advanced-group">
              <div class="advanced-group-title">{{ $t('settings.advanced.webSearch') }}</div>
              <div class="field-row">
                <label class="field-label">Model</label>
                <input
                  v-model="form.web_search_model"
                  class="field-input ms-input"
                  type="text"
                  placeholder="e.g. google/gemini-2.0-flash-001:online"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- Neo4j Configuration -->
        <section class="settings-section">
          <div class="section-header">
            <span class="section-label">{{ $t('settings.neo4j.title') }}</span>
          </div>

          <div class="field-row">
            <label class="field-label">URI</label>
            <input
              v-model="form.neo4j.uri"
              class="field-input ms-input"
              type="text"
              placeholder="bolt://localhost:7687"
            />
          </div>

          <div class="field-row">
            <label class="field-label">User</label>
            <input
              v-model="form.neo4j.user"
              class="field-input ms-input"
              type="text"
              placeholder="neo4j"
            />
          </div>

          <div class="field-row">
            <label class="field-label">Password</label>
            <input
              v-model="form.neo4j.password"
              class="field-input ms-input"
              type="password"
              placeholder="Leave blank to keep unchanged"
            />
          </div>
        </section>

        <!-- Outbound webhook · Slack / Discord / Zapier / n8n / custom -->
        <section class="settings-section ai-section">
          <div class="section-header">
            <span class="section-label">{{ $t('settings.webhook.title') }}</span>
            <div class="status-badge" :class="webhookSavedClass">
              <span class="badge-dot"></span>
              {{ webhookSavedText }}
            </div>
          </div>

          <div class="ai-intro">
            POST a JSON summary to your URL the moment a simulation finishes —
            wires Slack, Discord, Zapier, Make, n8n, IFTTT, or any custom listener.
            Empty to disable. Payload includes scenario, final consensus, quality,
            and the share-card URL so links auto-unfurl.
          </div>

          <div class="field-row">
            <label class="field-label">Webhook URL</label>
            <input
              v-model="form.integrations.webhook.url"
              class="field-input ms-input"
              type="text"
              :placeholder="webhookPlaceholder"
              autocomplete="off"
              spellcheck="false"
            />
            <div class="field-hint">
              e.g.
              <code>https://hooks.slack.com/services/T0…/B0…/abc</code>
              or any URL that accepts a POST.
              See <a href="https://github.com/aaronjmars/MiroShark/blob/main/docs/WEBHOOKS.md"
                     target="_blank" rel="noopener">the webhook docs</a>
              for the payload schema.
            </div>
          </div>

          <div class="field-row">
            <label class="field-label">Public base URL <span class="field-label-optional">(optional)</span></label>
            <input
              v-model="form.integrations.webhook.public_base_url"
              class="field-input ms-input"
              type="text"
              placeholder="https://miroshark.app"
              autocomplete="off"
              spellcheck="false"
            />
            <div class="field-hint">
              When set, the payload includes absolute <code>share_url</code> +
              <code>share_card_url</code> so Slack &amp; Discord auto-unfurl
              with the simulation card. Leave blank for relative paths only.
            </div>
          </div>

          <div class="field-row webhook-actions">
            <button
              class="ai-retry"
              :disabled="webhookTesting || !webhookCanTest"
              @click="testWebhookFire"
            >
              {{ webhookTesting ? $t('settings.webhook.testing') : $t('settings.webhook.testBtn') }}
            </button>
            <span v-if="webhookTestResult" class="webhook-test-result" :class="webhookTestResult.success ? 'ok' : 'fail'">
              <template v-if="webhookTestResult.success">
                ✓ Delivered ({{ webhookTestResult.latency_ms }}ms)
              </template>
              <template v-else>
                ✗ {{ webhookTestResult.error || webhookTestResult.message || 'Failed' }}
              </template>
            </span>
          </div>
        </section>

        <!-- AI Integration (MCP) -->
        <section class="settings-section ai-section">
          <div class="section-header">
            <span class="section-label">{{ $t('settings.mcp.title') }}</span>
            <div class="status-badge" :class="mcpHealthClass">
              <span class="badge-dot"></span>
              {{ mcpHealthText }}
            </div>
          </div>

          <div class="ai-intro">
            Wire MiroShark's knowledge graph into Claude Desktop, Cursor, Windsurf,
            or Continue. Pick your client, paste the snippet, restart the editor.
          </div>

          <div v-if="mcpLoading" class="ai-loading">Loading MCP catalog…</div>
          <div v-else-if="mcpLoadError" class="ai-error">
            {{ mcpLoadError }}
            <button class="ai-retry" @click="loadMcpStatus">Retry</button>
          </div>

          <div v-else-if="mcpStatus" class="ai-body">
            <!-- Health summary grid -->
            <div class="ai-summary">
              <div class="ai-summary-row">
                <span class="ai-summary-key">Server file</span>
                <span class="ai-summary-val" :class="mcpStatus.paths.mcp_script_exists ? '' : 'setup-missing'">
                  {{ mcpStatus.paths.mcp_script_exists ? 'present' : 'missing' }}
                </span>
              </div>
              <div class="ai-summary-row">
                <span class="ai-summary-key">Tools exposed</span>
                <span class="ai-summary-val">{{ mcpStatus.tool_count }}</span>
              </div>
              <div class="ai-summary-row">
                <span class="ai-summary-key">Neo4j</span>
                <span class="ai-summary-val" :class="mcpStatus.neo4j.connected ? '' : 'setup-missing'">
                  {{ mcpStatus.neo4j.connected ? 'connected' : 'unreachable' }}
                </span>
              </div>
              <div class="ai-summary-row" v-if="mcpStatus.neo4j.connected">
                <span class="ai-summary-key">Graphs available</span>
                <span class="ai-summary-val">
                  {{ mcpStatus.neo4j.graph_count ?? 0 }}
                  <span class="setup-aux" v-if="mcpStatus.neo4j.entity_count != null">
                    ({{ mcpStatus.neo4j.entity_count }} entities)
                  </span>
                </span>
              </div>
              <div class="ai-summary-row" v-if="mcpStatus.neo4j.error">
                <span class="ai-summary-key">Error</span>
                <span class="ai-summary-val ai-error-text">{{ mcpStatus.neo4j.error }}</span>
              </div>
            </div>

            <!-- Client tabs -->
            <div class="ai-tabs" role="tablist">
              <button
                v-for="key in clientOrder"
                :key="key"
                class="ai-tab"
                :class="{ active: activeClient === key }"
                role="tab"
                :aria-selected="activeClient === key"
                @click="activeClient = key"
              >
                {{ mcpStatus.clients[key]?.label || key }}
              </button>
            </div>

            <!-- Active client snippet -->
            <div v-if="currentClient" class="ai-client">
              <div class="ai-client-file">
                <span class="ai-client-file-label">Config file:</span>
                <code class="ai-client-file-path">{{ currentClient.file }}</code>
              </div>
              <div class="ai-snippet-wrap">
                <pre class="ai-snippet"><code>{{ formatJson(currentClient.config) }}</code></pre>
                <button
                  class="ai-copy-btn"
                  :class="{ ok: copyState === 'ok', fail: copyState === 'fail' }"
                  @click="copySnippet"
                >
                  {{ copyButtonLabel }}
                </button>
              </div>
              <div v-if="currentClient.notes" class="ai-client-notes">
                {{ currentClient.notes }}
              </div>
            </div>

            <!-- Tool catalog (collapsed by default) -->
            <button class="ai-tools-toggle" @click="toolsOpen = !toolsOpen">
              <span>{{ toolsOpen ? '▾' : '▸' }} {{ mcpStatus.tool_count }} tools available</span>
            </button>
            <ul v-if="toolsOpen" class="ai-tools-list">
              <li v-for="t in mcpStatus.tools" :key="t.name" class="ai-tool">
                <code class="ai-tool-name">{{ t.name }}</code>
                <span class="ai-tool-desc">{{ t.description }}</span>
              </li>
            </ul>

            <div class="ai-docs-link">
              Need a deeper walkthrough?
              <a :href="mcpStatus.docs_url" target="_blank" rel="noopener">Read the full MCP guide →</a>
            </div>
          </div>
        </section>

        <!-- Footer -->
        <div class="modal-footer">
          <div v-if="saveError" class="save-error">{{ saveError }}</div>
          <div v-if="saveSuccess" class="save-success">✓ Settings saved (runtime — edit .env to persist across restarts)</div>
          <div class="footer-actions">
            <button class="cancel-btn" @click="$emit('close')">Cancel</button>
            <button class="save-btn" :disabled="saving" @click="saveSettings">
              <span v-if="saving">Saving...</span>
              <span v-else>Save Settings →</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getSettings, updateSettings, testLlmConnection, testWebhook } from '../api/settings'
import { getMcpStatus } from '../api/mcp'

const { t } = useI18n()

const props = defineProps({
  open: { type: Boolean, required: true }
})

const emit = defineEmits(['close'])

// ─── Provider catalog & curated model lists ───────────────────────────────────

const PROVIDER_CATALOG = [
  { id: 'openrouter', name: 'OpenRouter', url: 'https://openrouter.ai/api/v1', prefix: (k) => k.startsWith('sk-or-v1-') },
  { id: 'moonshot',   name: 'Moonshot / Kimi', url: 'https://api.moonshot.ai/v1', prefix: (k) => /^eyJ[A-Za-z0-9+/=_-]{10,}/.test(k) },
  { id: 'anthropic',  name: 'Anthropic', url: 'https://api.anthropic.com/v1', prefix: (k) => k.startsWith('sk-ant-api0') },
  { id: 'groq',       name: 'Groq', url: 'https://api.groq.com/openai/v1', prefix: (k) => k.startsWith('gsk_') },
  { id: 'google',     name: 'Google Gemini', url: 'https://generativelanguage.googleapis.com/v1beta/openai', prefix: (k) => k.startsWith('AIza') },
  { id: 'openai',     name: 'OpenAI', url: 'https://api.openai.com/v1', prefix: (k) => k.startsWith('sk-') },
]

const CURATED_MODELS = {
  openrouter: [
    { id: 'moonshotai/kimi-k2', name: 'Kimi K2 Turbo (recommandé)', desc: 'Rapide · Bas coût' },
    { id: 'anthropic/claude-sonnet-4-6', name: 'Claude Sonnet 4.6', desc: 'Intelligent · Rapports' },
    { id: 'google/gemini-2.0-flash-001', name: 'Gemini 2.0 Flash', desc: 'Rapide · Multimodal' },
    { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', desc: 'Économique' },
    { id: 'openai/gpt-4o', name: 'GPT-4o', desc: 'Puissant' },
  ],
  moonshot: [
    { id: 'kimi-k2-turbo-preview', name: 'Kimi K2 Turbo (recommandé)', desc: 'Très rapide' },
    { id: 'moonshot-v1-32k', name: 'Moonshot V1 32K', desc: 'Contexte long' },
  ],
  anthropic: [
    { id: 'claude-sonnet-4-6-20251022', name: 'Claude Sonnet 4.6', desc: 'Recommandé' },
    { id: 'claude-haiku-4-5-20251001', name: 'Claude Haiku 4.5', desc: 'Rapide' },
  ],
  groq: [
    { id: 'llama-3.3-70b-versatile', name: 'LLaMA 3.3 70B', desc: 'Gratuit · Très rapide' },
    { id: 'moonshotai/kimi-k2', name: 'Kimi K2', desc: 'Reasoning' },
  ],
  google: [
    { id: 'gemini-2.0-flash-001', name: 'Gemini 2.0 Flash', desc: 'Rapide · Multimodal' },
    { id: 'gemini-1.5-pro-002', name: 'Gemini 1.5 Pro', desc: 'Puissant' },
  ],
  openai: [
    { id: 'gpt-4o', name: 'GPT-4o', desc: 'Meilleur OpenAI' },
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini', desc: 'Économique' },
  ],
}

const detectProvider = (key) => {
  if (!key || key.length < 8) return null
  return PROVIDER_CATALOG.find(p => p.prefix(key)) || null
}

// Current settings loaded from backend
const currentSettings = ref({})

// Form state
const form = reactive({
  preset: '',
  presetApiKey: '',
  llm: {
    provider: 'openai',
    base_url: '',
    model_name: '',
    api_key: '',
  },
  smart: { model_name: '' },
  ner: { model_name: '' },
  wonderwall: { model_name: '' },
  embedding: { provider: 'ollama', model_name: '' },
  web_search_model: '',
  neo4j: {
    uri: '',
    user: '',
    password: '',
  },
  integrations: {
    webhook: {
      url: '',
      public_base_url: '',
    },
  },
})

// UI state
const showKey = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)
const testing = ref(false)
const testResult = ref(null)
const modelList = ref([])
const loadingModels = ref(false)
const modelLoadError = ref('')
const advancedOpen = ref(false)
const inheritMarker = '— inherits default —'
const customModelInput = ref('')
const curatedModelList = ref([])

// Webhook integration state
const webhookTesting = ref(false)
const webhookTestResult = ref(null)

// MCP / AI Integration state
const mcpStatus = ref(null)
const mcpLoading = ref(false)
const mcpLoadError = ref('')
const clientOrder = ['claude_desktop', 'cursor', 'windsurf', 'continue', 'fallback_direct']
const activeClient = ref('claude_desktop')
const toolsOpen = ref(false)
const copyState = ref('') // '' | 'ok' | 'fail'

// ─── Auto-détection provider ──────────────────────────────────────────────────

const detectedProvider = computed(() => detectProvider(form.llm.api_key || ''))

watch(() => form.llm.api_key, (newKey) => {
  const p = detectProvider(newKey)
  if (p && !form.llm.base_url) {
    form.llm.base_url = p.url
  }
  if (p && CURATED_MODELS[p.id]) {
    // auto-sélectionner le premier modèle recommandé si modèle vide
    if (!form.llm.model_name) {
      form.llm.model_name = CURATED_MODELS[p.id][0].id
    }
    curatedModelList.value = CURATED_MODELS[p.id]
  } else {
    curatedModelList.value = []
  }
})

// ─── Load current settings when panel opens ───────────────────────────────────

watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    saveError.value = ''
    saveSuccess.value = false
    testResult.value = null
    webhookTestResult.value = null
    form.preset = ''
    form.presetApiKey = ''
    copyState.value = ''
    await Promise.all([loadCurrentSettings(), loadMcpStatus()])
  }
})

const loadCurrentSettings = async () => {
  try {
    // Axios response interceptor already unwraps to the body, so `res`
    // is `{ success, data }` — not the raw axios response.
    const res = await getSettings()
    if (res?.success && res.data) {
      const d = res.data
      currentSettings.value = d
      form.llm.provider = d.llm.provider || 'openai'
      form.llm.base_url = d.llm.base_url || ''
      form.llm.model_name = d.llm.model_name || ''
      form.llm.api_key = '' // never pre-fill
      form.smart.model_name = d.smart?.model_name || ''
      form.ner.model_name = d.ner?.model_name || ''
      form.wonderwall.model_name = d.wonderwall?.model_name || ''
      form.embedding.provider = d.embedding?.provider || 'ollama'
      form.embedding.model_name = d.embedding?.model_name || ''
      form.web_search_model = d.web_search_model || ''
      form.neo4j.uri = d.neo4j?.uri || ''
      form.neo4j.user = d.neo4j?.user || ''
      form.neo4j.password = ''
      // Webhook URL is masked server-side — never round-trip the masked
      // form back as a value the user could accidentally save. Leave the
      // input blank when configured so editing is explicit.
      form.integrations.webhook.url = ''
      form.integrations.webhook.public_base_url = d.integrations?.webhook?.public_base_url || ''
    }
  } catch (_) {
    // Non-fatal
  }
}

const presetOptions = computed(() => currentSettings.value.available_presets || [])

// `local` preset doesn't need an API key — the others do.
const presetNeedsKey = computed(() =>
  form.preset === 'cheap' || form.preset === 'best'
)

// Whether current base URL is OpenRouter
const isOpenRouter = computed(() =>
  form.llm.base_url.includes('openrouter.ai')
)

// Model tiering thresholds (cost per 1M tokens, prompt side)
const MODEL_TIERS = [
  { label: 'Fast (< $0.50/M)', max: 0.5 },
  { label: 'Standard ($0.50–$5/M)', max: 5 },
  { label: 'Capable (> $5/M)', max: Infinity },
]

const modelTiers = computed(() => {
  if (modelList.value.length === 0) return []
  return MODEL_TIERS.map(tier => ({
    label: tier.label,
    models: modelList.value.filter(m => {
      const price = m.pricing?.prompt ? parseFloat(m.pricing.prompt) * 1_000_000 : 0
      return price <= tier.max && price > (tier === MODEL_TIERS[0] ? 0 : MODEL_TIERS[MODEL_TIERS.indexOf(tier) - 1].max)
    })
  })).filter(t => t.models.length > 0)
})

const loadOpenRouterModels = async () => {
  loadingModels.value = true
  modelLoadError.value = ''
  try {
    const res = await fetch('https://openrouter.ai/api/v1/models')
    const json = await res.json()
    if (json.data) {
      modelList.value = json.data
        .filter(m => m.id && m.name)
        .sort((a, b) => {
          const pa = parseFloat(a.pricing?.prompt || 0) * 1_000_000
          const pb = parseFloat(b.pricing?.prompt || 0) * 1_000_000
          return pa - pb
        })
    }
  } catch (_) {
    modelLoadError.value = 'Could not load model list — check your network connection.'
  } finally {
    loadingModels.value = false
  }
}

const testConnection = async () => {
  testing.value = true
  testResult.value = null
  try {
    // Interceptor unwraps axios to the body directly.
    const res = await testLlmConnection()
    testResult.value = res
  } catch (e) {
    testResult.value = { success: false, error: e.message }
  } finally {
    testing.value = false
  }
}

const loadMcpStatus = async () => {
  mcpLoading.value = true
  mcpLoadError.value = ''
  try {
    // Axios interceptor unwraps to { success, data }.
    const res = await getMcpStatus()
    if (res?.success && res.data) {
      mcpStatus.value = res.data
    } else {
      mcpLoadError.value = res?.error || 'MCP status unavailable'
    }
  } catch (e) {
    mcpLoadError.value = e?.message || 'MCP status request failed'
  } finally {
    mcpLoading.value = false
  }
}

const currentClient = computed(() => {
  if (!mcpStatus.value) return null
  return mcpStatus.value.clients?.[activeClient.value] || null
})

const mcpHealthClass = computed(() => {
  if (!mcpStatus.value) return 'idle'
  if (!mcpStatus.value.paths.mcp_script_exists) return 'fail'
  return mcpStatus.value.neo4j.connected ? 'ok' : 'fail'
})

const mcpHealthText = computed(() => {
  if (!mcpStatus.value) return 'Loading'
  if (!mcpStatus.value.paths.mcp_script_exists) return 'Server file missing'
  return mcpStatus.value.neo4j.connected ? 'Ready' : 'Neo4j down'
})

const formatJson = (obj) => JSON.stringify(obj, null, 2)

const copyButtonLabel = computed(() => {
  if (copyState.value === 'ok') return '✓ Copied'
  if (copyState.value === 'fail') return '✗ Copy failed'
  return 'Copy snippet'
})

const copySnippet = async () => {
  if (!currentClient.value) return
  const text = formatJson(currentClient.value.config)
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      // Fallback for older / non-secure-context browsers.
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      if (!ok) throw new Error('execCommand copy returned false')
    }
    copyState.value = 'ok'
  } catch (_) {
    copyState.value = 'fail'
  } finally {
    setTimeout(() => { copyState.value = '' }, 2200)
  }
}

const testStatus = computed(() => {
  if (!testResult.value) return 'idle'
  return testResult.value.success ? 'ok' : 'fail'
})

const testStatusText = computed(() => {
  if (!testResult.value) return 'Not tested'
  return testResult.value.success ? 'Connected' : 'Failed'
})

const webhookConfigured = computed(() =>
  Boolean(currentSettings.value.integrations?.webhook?.configured)
)

const webhookSavedClass = computed(() => (webhookConfigured.value ? 'ok' : 'idle'))
const webhookSavedText = computed(() =>
  webhookConfigured.value ? 'Configured' : 'Not configured'
)

const webhookPlaceholder = computed(() => {
  if (webhookConfigured.value) {
    const masked = currentSettings.value.integrations?.webhook?.url_masked
    return masked
      ? `${masked} — leave blank to keep, type to replace`
      : 'Leave blank to keep saved URL, type to replace'
  }
  return 'https://hooks.slack.com/services/T0…/B0…/abc'
})

// The button can fire when there's a typed URL OR a saved one to retry.
const webhookCanTest = computed(() =>
  Boolean(form.integrations.webhook.url?.trim()) || webhookConfigured.value
)

const testWebhookFire = async () => {
  webhookTesting.value = true
  webhookTestResult.value = null
  try {
    const url = form.integrations.webhook.url?.trim() || ''
    const baseUrl = form.integrations.webhook.public_base_url?.trim() || ''
    const res = await testWebhook(url, baseUrl)
    webhookTestResult.value = res
  } catch (e) {
    webhookTestResult.value = { success: false, error: e?.message || 'Network error' }
  } finally {
    webhookTesting.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  saveError.value = ''
  saveSuccess.value = false
  try {
    const payload = {}

    // Preset is applied server-side first; explicit field overrides apply on top.
    if (form.preset) {
      payload.preset = form.preset
      if (form.presetApiKey) payload.preset_api_key = form.presetApiKey
    }

    payload.llm = {
      provider: form.llm.provider,
      base_url: form.llm.base_url,
      model_name: form.llm.model_name,
    }
    if (form.llm.api_key) payload.llm.api_key = form.llm.api_key

    payload.smart = { model_name: form.smart.model_name }
    payload.ner = { model_name: form.ner.model_name }
    payload.wonderwall = { model_name: form.wonderwall.model_name }
    payload.embedding = {
      provider: form.embedding.provider,
      model_name: form.embedding.model_name,
    }
    payload.web_search_model = form.web_search_model

    payload.neo4j = {
      uri: form.neo4j.uri,
      user: form.neo4j.user,
    }
    if (form.neo4j.password) payload.neo4j.password = form.neo4j.password

    // Webhook integration — only send `url` when the user actually typed
    // something (blank input means "keep what's saved"). The base URL is
    // always sent because clearing it should be a deliberate action.
    const wh = {}
    const typedUrl = form.integrations.webhook.url?.trim()
    if (typedUrl !== undefined && typedUrl !== '') {
      wh.url = typedUrl
    }
    wh.public_base_url = form.integrations.webhook.public_base_url?.trim() || ''
    payload.integrations = { webhook: wh }

    const res = await updateSettings(payload)
    if (res?.success && res.data) {
      saveSuccess.value = true
      currentSettings.value = res.data
      form.llm.api_key = ''
      form.presetApiKey = ''
      form.neo4j.password = ''
      // Reset the webhook URL input so the placeholder shows the new
      // masked value and we don't accidentally re-save the same string.
      form.integrations.webhook.url = ''
      setTimeout(() => { saveSuccess.value = false }, 4000)
    } else {
      saveError.value = res?.error || 'Save failed'
    }
  } catch (e) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* ── Modal Overlay — refonte Warm Intelligence ── */
.settings-overlay {
  position: fixed;
  inset: 0;
  background: var(--ms-bg-overlay);
  z-index: var(--ms-z-modal-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fade-in 0.15s ease-out;
  backdrop-filter: blur(4px);
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.settings-modal {
  background: var(--wi-surface);
  width: 580px;
  max-width: calc(100vw - 48px);
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-lg);
  position: relative;
  animation: slide-in 0.2s ease-out;
  font-family: var(--wi-font-body);
  color: var(--wi-on-surface);
  z-index: var(--ms-z-modal);
}

@keyframes slide-in {
  from { transform: translateY(-16px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* ── Header ── */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--wi-space-md);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  border-block-end: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card) var(--wi-radius-card) 0 0;
  position: sticky;
  top: 0;
  z-index: 1;
}

.title-label {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  letter-spacing: -0.005em;
  color: var(--wi-on-surface);
  text-transform: none;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--wi-on-surface-variant);
  font-size: 18px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: var(--wi-radius-sm);
  transition: color var(--ms-transition-fast), background var(--ms-transition-fast);
}
.close-btn:hover {
  color: var(--wi-on-surface);
  background: var(--wi-surface-container-high);
}

/* ── Warning Stripe (terracotta + cream) ── */
.warning-stripe {
  height: 4px;
  background: repeating-linear-gradient(
    -45deg,
    var(--wi-on-primary-container),
    var(--wi-on-primary-container) 10px,
    var(--wi-surface-container-low) 10px,
    var(--wi-surface-container-low) 20px
  );
}

/* ── Sections ── */
.settings-section {
  padding: var(--wi-space-md);
  border-bottom: 1px solid var(--wi-outline-variant);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.section-label {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-label-sm);
  font-weight: var(--wi-label-sm-weight);
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
}

/* ── Current Setup grid ── */
.setup-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  padding: 14px 16px;
  background: var(--wi-surface-container-low);
}
.setup-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  font-size: var(--wi-caption);
  letter-spacing: 0.3px;
}
.setup-key {
  color: var(--wi-on-surface-variant);
  flex-shrink: 0;
}
.setup-val {
  color: var(--wi-on-surface);
  font-weight: 600;
  text-align: end;
  overflow-wrap: anywhere;
  font-family: var(--ms-font-mono);
}
.setup-aux {
  color: var(--wi-outline);
  font-weight: 400;
  margin-inline-start: 4px;
}
.setup-missing {
  color: var(--wi-error);
  font-weight: 400;
}

/* ── Status Badge ── */
.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--wi-caption);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-weight: 600;
}

.badge-dot {
  width: 7px;
  height: 7px;
  background: var(--wi-outline);
  border-radius: 50%;
}
.status-badge.ok .badge-dot { background: var(--wi-secondary); }
.status-badge.fail .badge-dot { background: var(--wi-error); }
.status-badge.ok { color: var(--wi-secondary); }
.status-badge.fail { color: var(--wi-error); }
.status-badge.idle { color: var(--wi-outline); }

/* ── Form Fields ── */
.field-row {
  margin-bottom: 14px;
}

.field-label {
  display: block;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  margin-bottom: 6px;
}

.field-input {
  width: 100%;
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface-container-low);
  padding: 10px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface);
  outline: none;
  border-radius: var(--wi-radius-interactive);
  transition: border-color var(--ms-transition-fast), box-shadow var(--ms-transition-fast);
  box-sizing: border-box;
}
.field-input:focus {
  border-color: var(--wi-primary-container);
  box-shadow: 0 0 0 2px var(--wi-primary-container-soft);
  background: var(--wi-surface);
}
.field-input::placeholder { color: var(--wi-outline); }

.select-wrapper { position: relative; }
.field-select {
  width: 100%;
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface-container-low);
  padding: 10px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface);
  outline: none;
  cursor: pointer;
  appearance: auto;
  border-radius: var(--wi-radius-interactive);
  transition: border-color var(--ms-transition-fast), box-shadow var(--ms-transition-fast);
  box-sizing: border-box;
}
.field-select:focus {
  border-color: var(--wi-primary-container);
  box-shadow: 0 0 0 2px var(--wi-primary-container-soft);
}

/* ── Model input group ── */
.model-input-group {
  display: flex;
  gap: 6px;
}
.model-select-wrapper { flex: 1; min-width: 0; }

.load-models-btn {
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface-container-low);
  padding: 10px 14px;
  font-family: var(--wi-font-body);
  font-size: 14px;
  cursor: pointer;
  border-radius: var(--wi-radius-interactive);
  color: var(--wi-on-surface-variant);
  transition: border-color var(--ms-transition-fast), color var(--ms-transition-fast);
  flex-shrink: 0;
}
.load-models-btn:hover:not(:disabled) {
  border-color: var(--wi-on-primary-container);
  color: var(--wi-on-primary-container);
}
.load-models-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Key input group ── */
.key-input-group {
  display: flex;
  gap: 6px;
}
.key-input-group .field-input { flex: 1; }

.toggle-key-btn {
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface-container-low);
  padding: 10px 14px;
  font-size: 14px;
  cursor: pointer;
  flex-shrink: 0;
  border-radius: var(--wi-radius-interactive);
  color: var(--wi-on-surface-variant);
  transition: border-color var(--ms-transition-fast);
}
.toggle-key-btn:hover { border-color: var(--wi-on-primary-container); }

.field-hint {
  margin-top: 6px;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  letter-spacing: 0.3px;
  line-height: 1.5;
}
.field-hint a { color: var(--wi-on-primary-container); text-decoration: underline; }
.field-hint code {
  font-family: var(--ms-font-mono);
  background: var(--wi-surface-container-high);
  padding: 1px 5px;
  border-radius: var(--wi-radius-sm);
  font-size: 0.9em;
}

.field-error {
  margin-top: 6px;
  font-size: var(--wi-caption);
  color: var(--wi-error);
}

/* ── Test row ── */
.test-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.test-btn {
  border: 1px solid var(--wi-outline-variant);
  background: transparent;
  padding: 10px 18px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  cursor: pointer;
  border-radius: var(--wi-radius-interactive);
  color: var(--wi-on-surface-variant);
  transition: border-color var(--ms-transition-fast), color var(--ms-transition-fast);
}
.test-btn:hover:not(:disabled) {
  border-color: var(--wi-on-primary-container);
  color: var(--wi-on-primary-container);
}
.test-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.test-result {
  font-size: var(--wi-caption);
  letter-spacing: 0.5px;
}
.test-result.ok { color: var(--wi-secondary); }
.test-result.fail { color: var(--wi-error); }

/* ── Advanced ── */
.advanced-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  background: transparent;
  border: none;
  padding: 0 0 10px 0;
  cursor: pointer;
  font-family: var(--wi-font-body);
}
.chevron {
  font-size: 16px;
  color: var(--wi-on-surface-variant);
  line-height: 1;
}
.advanced-body {
  margin-top: 4px;
}
.advanced-hint {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  margin-bottom: 12px;
  letter-spacing: 0.3px;
  line-height: 1.5;
}
.advanced-group {
  padding: 12px 0;
  border-top: 1px dashed var(--wi-outline-variant);
}
.advanced-group:first-child { border-top: none; padding-top: 0; }
.advanced-group-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--wi-on-surface);
  margin-bottom: 10px;
}

/* ── Footer ── */
.modal-footer {
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--wi-surface);
  border-radius: 0 0 var(--wi-radius-card) var(--wi-radius-card);
  position: sticky;
  bottom: 0;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.save-error {
  font-size: var(--wi-caption);
  color: var(--wi-error);
  letter-spacing: 0.3px;
}

.save-success {
  font-size: var(--wi-caption);
  color: var(--wi-secondary);
  letter-spacing: 0.5px;
}

.cancel-btn {
  border: 1px solid var(--wi-outline-variant);
  background: transparent;
  padding: 12px 22px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  cursor: pointer;
  color: var(--wi-on-surface-variant);
  border-radius: var(--wi-radius-interactive);
  transition: border-color var(--ms-transition-fast), color var(--ms-transition-fast), background var(--ms-transition-fast);
}
.cancel-btn:hover {
  border-color: var(--wi-outline);
  color: var(--wi-on-surface);
  background: var(--wi-surface-container-low);
}

.save-btn {
  border: 1px solid var(--wi-on-primary-container);
  background: var(--wi-on-primary-container);
  color: var(--wi-bg);
  padding: 12px 22px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  cursor: pointer;
  border-radius: var(--wi-radius-interactive);
  transition: opacity var(--ms-transition-fast), box-shadow var(--ms-transition-fast);
}
.save-btn:hover:not(:disabled) {
  opacity: 0.92;
  box-shadow: var(--wi-shadow-md);
}
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Webhook integration row ── */
.webhook-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.webhook-test-result {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  letter-spacing: 0.3px;
}

.webhook-test-result.ok { color: var(--wi-secondary); }
.webhook-test-result.fail { color: var(--wi-error); }

.field-label-optional {
  color: var(--wi-outline);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  font-size: var(--wi-caption);
}

/* ── AI Integration (MCP) ── */
.ai-section {
  background: var(--wi-surface-container-low);
}

.ai-intro {
  font-size: var(--wi-body-md);
  line-height: 1.55;
  color: var(--wi-on-surface);
  margin-bottom: 14px;
}

.ai-loading,
.ai-error {
  font-size: var(--wi-caption);
  padding: 14px 16px;
  border: 1px dashed var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  background: var(--wi-surface);
}

.ai-error {
  color: var(--wi-error);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.ai-retry {
  background: var(--wi-on-primary-container);
  color: var(--wi-bg);
  border: none;
  padding: 8px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  cursor: pointer;
  border-radius: var(--wi-radius-interactive);
  transition: opacity var(--ms-transition-fast);
}
.ai-retry:hover { opacity: 0.92; }

.ai-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px dashed var(--wi-outline-variant);
  padding: 14px 16px;
  background: var(--wi-surface);
  border-radius: var(--wi-radius-md);
  margin-bottom: 14px;
}

.ai-summary-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  font-size: var(--wi-caption);
}

.ai-summary-key {
  color: var(--wi-on-surface-variant);
  flex-shrink: 0;
}

.ai-summary-val {
  color: var(--wi-on-surface);
  font-weight: 600;
  text-align: end;
  overflow-wrap: anywhere;
  font-family: var(--ms-font-mono);
}

.ai-error-text {
  color: var(--wi-error);
  font-weight: 400;
  font-size: var(--wi-caption);
}

.ai-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 0;
  border-bottom: 1px solid var(--wi-outline-variant);
}

.ai-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  padding: 10px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  transition: color var(--ms-transition-fast), border-color var(--ms-transition-fast);
}

.ai-tab:hover { color: var(--wi-on-surface); }

.ai-tab.active {
  color: var(--wi-on-primary-container);
  border-bottom-color: var(--wi-primary-container);
}

.ai-client {
  padding-top: 14px;
}

.ai-client-file {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  margin-bottom: 8px;
  overflow-wrap: anywhere;
}

.ai-client-file-label {
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-inline-end: 4px;
  font-weight: 600;
}

.ai-client-file-path {
  font-family: var(--ms-font-mono);
  color: var(--wi-on-surface);
  background: var(--wi-surface-container-high);
  padding: 2px 6px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-sm);
}

.ai-snippet-wrap {
  position: relative;
}

.ai-snippet {
  background: var(--wi-on-bg);
  color: var(--wi-bg);
  padding: 16px 18px;
  margin: 0;
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre;
  border: 1px solid var(--wi-on-bg);
  border-radius: var(--wi-radius-md);
}

.ai-snippet code {
  font: inherit;
  color: inherit;
}

.ai-copy-btn {
  position: absolute;
  top: 10px;
  inset-inline-end: 10px;
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
  border: none;
  padding: 6px 12px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  cursor: pointer;
  border-radius: var(--wi-radius-interactive);
  transition: background var(--ms-transition-fast), color var(--ms-transition-fast);
}

.ai-copy-btn:hover { background: var(--wi-secondary); color: var(--wi-on-secondary); }
.ai-copy-btn.ok { background: var(--wi-secondary); color: var(--wi-on-secondary); }
.ai-copy-btn.fail { background: var(--wi-error); color: var(--wi-on-error); }

.ai-client-notes {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  margin-top: 8px;
  line-height: 1.5;
}

.ai-tools-toggle {
  display: block;
  width: 100%;
  background: none;
  border: 1px dashed var(--wi-outline-variant);
  padding: 10px 14px;
  margin-top: 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  text-align: start;
  border-radius: var(--wi-radius-md);
  transition: border-color var(--ms-transition-fast), color var(--ms-transition-fast);
}

.ai-tools-toggle:hover {
  border-color: var(--wi-outline);
  color: var(--wi-on-surface);
}

.ai-tools-list {
  list-style: none;
  padding: 14px 16px;
  margin: 6px 0 0 0;
  background: var(--wi-surface);
  border: 1px dashed var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-tool {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 12px;
  font-size: var(--wi-caption);
  line-height: 1.5;
}

.ai-tool-name {
  color: var(--wi-on-primary-container);
  font-weight: 600;
  font-family: var(--ms-font-mono);
}

.ai-tool-desc {
  color: var(--wi-on-surface);
  overflow-wrap: anywhere;
}

.ai-docs-link {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  margin-top: 14px;
  text-align: end;
}

.ai-docs-link a {
  color: var(--wi-on-surface);
  font-weight: 600;
  text-decoration: none;
  border-bottom: 1px solid var(--wi-on-primary-container);
}

.ai-docs-link a:hover { color: var(--wi-on-primary-container); }

@media (max-width: 480px) {
  .ai-tool {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}

/* ─── BYOK wizard ─── */
.byok-section {
  border: 1px solid var(--wi-primary-container-edge);
  border-inline-start: 3px solid var(--wi-on-primary-container);
  border-radius: var(--wi-radius-md);
  background: var(--wi-surface);
}
.byok-intro { color: var(--wi-on-surface-variant); font-size: var(--wi-body-md); margin: 0 0 1rem 0; line-height: 1.55; }

.provider-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: var(--wi-caption);
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  font-weight: 600;
}
.provider-badge--detected {
  background: var(--wi-secondary-soft);
  color: var(--wi-secondary);
}
.provider-badge--custom {
  background: var(--wi-primary-container-soft);
  color: var(--wi-on-primary-container);
}
.provider-badge-dot { font-size: 0.9em; }

.byok-key-input {
  font-family: var(--ms-font-mono);
  letter-spacing: 0.05em;
}
.byok-hint-detected {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
}

.byok-advanced { margin-top: 0.75rem; }
.byok-advanced summary.byok-advanced-toggle {
  cursor: pointer;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  padding: 4px 0;
}

.byok-propagation-hint {
  margin-top: 1rem;
  padding: 12px 16px;
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  line-height: 1.5;
}
.byok-prop-icon { flex-shrink: 0; }
</style>
