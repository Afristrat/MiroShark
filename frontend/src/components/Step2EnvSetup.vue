<template>
  <div class="env-setup-panel">
    <div class="scroll-container">
      <!-- Step 01: Simulation Instance -->
      <div class="step-card" :class="{ 'active': phase === 0, 'completed': phase > 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">{{ $t('process.step2.step1.title') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 0" class="badge success"><span class="badge-dot"></span>{{ $t('process.common.completed') }}</span>
            <span v-else-if="simulationId" class="badge processing"><span class="badge-dot"></span>{{ $t('process.common.initializing') }}</span>
            <span v-else class="badge pending"><span class="badge-dot"></span>{{ $t('process.common.loading') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description">
            {{ $t('process.step2.step1.description') }}
          </p>

          <div v-if="simulationId" class="info-card">
            <div class="info-row" @click="copyValue(projectData?.project_id)">
              <span class="info-label">{{ $t('process.step2.step1.projectId') }}</span>
              <span class="info-value mono copyable">{{ projectData?.project_id }}</span>
            </div>
            <div class="info-row" @click="copyValue(projectData?.graph_id)">
              <span class="info-label">{{ $t('process.step2.step1.graphId') }}</span>
              <span class="info-value mono copyable">{{ projectData?.graph_id }}</span>
            </div>
            <div class="info-row" @click="copyValue(simulationId)">
              <span class="info-label">{{ $t('process.step2.step1.simulationId') }}</span>
              <span class="info-value mono copyable">{{ simulationId }}</span>
            </div>
            <div class="info-row" @click="copyValue(taskId)">
              <span class="info-label">{{ $t('process.step2.step1.taskId') }}</span>
              <span class="info-value mono copyable">{{ taskId || $t('process.step2.step1.asyncCompleted') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: Generate Agent Profiles -->
      <div class="step-card" :class="{ 'active': phase === 1, 'completed': phase > 1 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">{{ $t('process.step2.step2.title') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 1" class="badge success"><span class="badge-dot"></span>{{ $t('process.common.completed') }}</span>
            <span v-else-if="phase === 1" class="badge processing"><span class="badge-dot"></span>{{ prepareProgress }}%</span>
            <span v-else class="badge pending"><span class="badge-dot"></span>{{ $t('process.common.waiting') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ $t('process.step2.step2.description') }}
          </p>

          <!-- Profiles Stats -->
          <div v-if="profiles.length > 0" class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ profiles.length }}</span>
              <span class="stat-label">{{ $t('process.step2.step2.currentAgents') }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ expectedTotal || '-' }}</span>
              <span class="stat-label">{{ $t('process.step2.step2.expectedTotal') }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ totalTopicsCount }}</span>
              <span class="stat-label">{{ $t('process.step2.step2.seedTopics') }}</span>
            </div>
          </div>

          <!-- Profiles List Preview -->
          <div v-if="profiles.length > 0" class="profiles-preview">
            <div class="preview-header">
              <span class="preview-title">{{ $t('process.step2.step2.generatedProfiles') }}</span>
            </div>
            <div class="profiles-list">
              <div
                v-for="(profile, idx) in profilesExpanded ? profiles : profiles.slice(0, 4)"
                :key="idx"
                class="profile-card"
                @click="selectProfile(profile)"
              >
                <div class="profile-header">
                  <span class="profile-realname">{{ profile.username || $t('process.step2.step2.unknown') }}</span>
                  <span class="profile-username">@{{ profile.name || `agent_${idx}` }}</span>
                  <span v-if="profile.manually_added || profile._isManual" class="profile-manual-badge" title="Agent ajouté manuellement">✎</span>
                </div>
                <div class="profile-meta">
                  <span class="profile-profession">{{ profile.profession || $t('process.step2.step2.unknownProfession') }}</span>
                </div>
                <p class="profile-bio">{{ profile.bio || $t('process.step2.step2.noBio') }}</p>
                <div v-if="profile.interested_topics?.length" class="profile-topics">
                  <span
                    v-for="topic in profile.interested_topics.slice(0, 3)"
                    :key="topic"
                    class="topic-tag"
                  >{{ topic }}</span>
                  <span v-if="profile.interested_topics.length > 3" class="topic-more">
                    +{{ profile.interested_topics.length - 3 }}
                  </span>
                </div>
              </div>
            </div>
            <button
              v-if="profiles.length > 4"
              class="profiles-toggle"
              @click="profilesExpanded = !profilesExpanded"
            >
              {{ profilesExpanded ? $t('process.step2.step2.showLess') : $t('process.step2.step2.showAll', { count: profiles.length }) }}
            </button>
            <button
              v-if="phase >= 1"
              class="add-agent-btn ms-btn ms-btn-secondary ms-btn--sm"
              type="button"
              @click="showAddAgentModal = true"
            >
              + {{ $t('process.step2.step2.addAgent') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Step 03: Generate Simulation Config -->
      <div class="step-card" :class="{ 'active': phase === 2, 'completed': phase > 2, 'error': configError }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">{{ $t('process.step2.step3.title') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 2" class="badge success"><span class="badge-dot"></span>{{ $t('process.common.completed') }}</span>
            <span v-else-if="configError" class="badge error"><span class="badge-dot"></span>{{ $t('process.common.failed') }}</span>
            <span v-else-if="phase === 2" class="badge processing"><span class="badge-dot"></span>{{ $t('process.common.generating') }}</span>
            <span v-else class="badge pending"><span class="badge-dot"></span>{{ $t('process.common.waiting') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ $t('process.step2.step3.description') }}
          </p>

          <!-- Config Error Panel -->
          <div v-if="configError" class="config-error-panel">
            <div class="config-error-title">{{ $t('process.step2.step3.errorTitle') }}</div>
            <div class="config-error-msg">{{ configError }}</div>
            <div class="config-error-hint">
              {{ contextualErrorHint }}
            </div>
            <button
              class="retry-config-btn ms-btn ms-btn-danger ms-btn--sm"
              :disabled="isConfigRetrying"
              @click="handleConfigRetry"
            >
              <span v-if="isConfigRetrying" class="loading-spinner-small"></span>
              {{ isConfigRetrying ? $t('process.step2.step3.retrying') : $t('process.step2.step3.retry') }}
            </button>
          </div>

          <!-- Config Preview -->
          <div v-if="simulationConfig" class="config-detail-panel">
            <!-- Time Configuration -->
            <div class="config-block">
              <div class="config-grid">
                <div class="config-item">
                  <span class="config-item-label">{{ $t('process.step2.step3.duration') }}</span>
                  <span class="config-item-value">{{ $t('process.step2.step3.hours', { count: simulationConfig.time_config?.total_simulation_hours || '-' }) }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('process.step2.step3.perRound') }}</span>
                  <span class="config-item-value">{{ $t('process.step2.step3.minutes', { count: simulationConfig.time_config?.minutes_per_round || '-' }) }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('process.step2.step3.totalRounds') }}</span>
                  <span class="config-item-value">{{ $t('process.step2.step3.rounds', { count: Math.floor((simulationConfig.time_config?.total_simulation_hours * 60 / simulationConfig.time_config?.minutes_per_round)) || '-' }) }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('process.step2.step3.activePerHour') }}</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.agents_per_hour_min }}-{{ simulationConfig.time_config?.agents_per_hour_max }}</span>
                </div>
              </div>
              <div class="time-periods">
                <div class="period-item">
                  <span class="period-label">{{ $t('process.step2.step3.peakHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.peak_hours?.join(':00, ') }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.peak_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('process.step2.step3.workHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.work_hours?.[0] }}:00-{{ simulationConfig.time_config?.work_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.work_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('process.step2.step3.morningHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.morning_hours?.[0] }}:00-{{ simulationConfig.time_config?.morning_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.morning_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('process.step2.step3.offPeakHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.off_peak_hours?.[0] }}:00-{{ simulationConfig.time_config?.off_peak_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.off_peak_activity_multiplier }}</span>
                </div>
              </div>
            </div>

            <!-- Agent Configuration -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('process.step2.step3.agentConfig') }}</span>
                <span class="config-block-badge">{{ simulationConfig.agent_configs?.length || 0 }}</span>
              </div>
              <div class="agents-cards">
                <div
                  v-for="agent in agentCardsExpanded ? simulationConfig.agent_configs : simulationConfig.agent_configs?.slice(0, 2)"
                  :key="agent.agent_id"
                  class="agent-card"
                >
                  <!-- Card Header -->
                  <div class="agent-card-header">
                    <div class="agent-identity">
                      <span class="agent-id">{{ $t('process.step2.step3.agentLabel', { id: agent.agent_id }) }}</span>
                      <span class="agent-name">{{ agent.entity_name }}</span>
                    </div>
                    <div class="agent-tags">
                      <span class="agent-type">{{ agent.entity_type }}</span>
                      <span class="agent-stance" :class="'stance-' + agent.stance">{{ agent.stance }}</span>
                    </div>
                  </div>

                  <!-- Profile Info (from generated profiles) -->
                  <div v-if="getAgentProfile(agent.agent_id)" class="agent-profile-info">
                    <span class="profile-profession-tag">{{ getAgentProfile(agent.agent_id).profession || $t('process.step2.step2.unknown') }}</span>
                    <span v-if="getAgentProfile(agent.agent_id).country" class="profile-country-tag">{{ getAgentProfile(agent.agent_id).country }}</span>
                    <span v-if="getAgentProfile(agent.agent_id).mbti" class="profile-mbti-tag">{{ getAgentProfile(agent.agent_id).mbti }}</span>
                    <p class="profile-bio-snippet">{{ (getAgentProfile(agent.agent_id).bio || '').slice(0, 120) }}{{ (getAgentProfile(agent.agent_id).bio || '').length > 120 ? '...' : '' }}</p>
                  </div>

                  <!-- Active Timeline -->
                  <div class="agent-timeline">
                    <span class="timeline-label">{{ $t('process.step2.step3.activeHours') }}</span>
                    <div class="mini-timeline">
                      <div 
                        v-for="hour in 24" 
                        :key="hour - 1" 
                        class="timeline-hour"
                        :class="{ 'active': agent.active_hours?.includes(hour - 1) }"
                        :title="`${hour - 1}:00`"
                      ></div>
                    </div>
                    <div class="timeline-marks">
                      <span>0</span>
                      <span>6</span>
                      <span>12</span>
                      <span>18</span>
                      <span>24</span>
                    </div>
                  </div>

                  <!-- Behavioral Parameters -->
                  <div class="agent-params">
                    <div class="param-group">
                      <div class="param-item">
                        <span class="param-label">{{ $t('process.step2.step3.postsPerHour') }}</span>
                        <span class="param-value">{{ agent.posts_per_hour }}</span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('process.step2.step3.commentsPerHour') }}</span>
                        <span class="param-value">{{ agent.comments_per_hour }}</span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('process.step2.step3.responseDelay') }}</span>
                        <span class="param-value">{{ $t('process.step2.step3.responseDelayMin', { min: agent.response_delay_min, max: agent.response_delay_max }) }}</span>
                      </div>
                    </div>
                    <div class="param-group">
                      <div class="param-item">
                        <span class="param-label">{{ $t('process.step2.step3.activityLevel') }}</span>
                        <span class="param-value with-bar">
                          <span class="mini-bar" :style="{ width: (agent.activity_level * 100) + '%' }"></span>
                          {{ (agent.activity_level * 100).toFixed(0) }}%
                        </span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('process.step2.step3.sentimentTendency') }}</span>
                        <span class="param-value" :class="agent.sentiment_bias > 0 ? 'positive' : agent.sentiment_bias < 0 ? 'negative' : 'neutral'">
                          {{ agent.sentiment_bias > 0 ? '+' : '' }}{{ agent.sentiment_bias?.toFixed(1) }}
                        </span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('process.step2.step3.influence') }}</span>
                        <span class="param-value highlight">{{ agent.influence_weight?.toFixed(1) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <button
                v-if="simulationConfig.agent_configs?.length > 2"
                class="profiles-toggle"
                @click="agentCardsExpanded = !agentCardsExpanded"
              >
                {{ agentCardsExpanded ? $t('process.step2.step2.showLess') : $t('process.step2.step2.showAll', { count: simulationConfig.agent_configs.length }) }}
              </button>
            </div>

            <!-- Platform Configuration -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('process.step2.step3.recAlgo') }}</span>
              </div>
              <div class="platforms-grid">
                <div v-if="simulationConfig.twitter_config" class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">X (Twitter)</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.timelinessWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.recency_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.popularityWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.popularity_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.relevanceWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.relevance_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.viralThreshold') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.viral_threshold }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.echoChamber') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.echo_chamber_strength }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="simulationConfig.reddit_config" class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">Reddit</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.timelinessWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.recency_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.popularityWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.popularity_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.relevanceWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.relevance_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.viralThreshold') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.viral_threshold }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.echoChamber') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.echo_chamber_strength }}</span>
                    </div>
                  </div>
                </div>
                <div class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">Polymarket</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.marketMaker') }}</span>
                      <span class="param-value">{{ $t('process.step2.step3.marketMakerVal') }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.initialLiquidity') }}</span>
                      <span class="param-value">{{ $t('process.step2.step3.initialLiquidityVal') }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.tradingActions') }}</span>
                      <span class="param-value">{{ $t('process.step2.step3.tradingActionsVal') }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('process.step2.step3.marketBridge') }}</span>
                      <span class="param-value">{{ $t('process.step2.step3.marketBridgeVal') }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- LLM Configuration Reasoning -->
            <div v-if="simulationConfig.generation_reasoning" class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('process.step2.step3.llmReasoning') }}</span>
              </div>
              <div class="reasoning-content">
                <div 
                  v-for="(reason, idx) in simulationConfig.generation_reasoning.split('|').slice(0, 2)" 
                  :key="idx" 
                  class="reasoning-item"
                >
                  <p class="reasoning-text">{{ reason.trim() }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 04: Initial Activation Orchestration -->
      <div class="step-card" :class="{ 'active': phase === 3, 'completed': phase > 3 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">04</span>
            <span class="step-title">{{ $t('process.step2.step4.title') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 3" class="badge success"><span class="badge-dot"></span>{{ $t('process.common.completed') }}</span>
            <span v-else-if="phase === 3" class="badge processing"><span class="badge-dot"></span>{{ $t('process.common.processing') }}</span>
            <span v-else class="badge pending"><span class="badge-dot"></span>{{ $t('process.common.waiting') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ $t('process.step2.step4.description') }}
          </p>

          <div v-if="simulationConfig?.event_config" class="orchestration-content">
            <!-- Narrative Direction -->
            <div class="narrative-box">
              <span class="box-label narrative-label">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="special-icon">
                  <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="url(#paint0_linear)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                  <path d="M16.24 7.76L14.12 14.12L7.76 16.24L9.88 9.88L16.24 7.76Z" fill="url(#paint0_linear)" stroke="url(#paint0_linear)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                  <defs>
                    <linearGradient id="paint0_linear" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#6d2400" />
                      <stop offset="1" stop-color="#ff8551" />
                    </linearGradient>
                  </defs>
                </svg>
                {{ $t('process.step2.step4.narrativeGuidance') }}
              </span>
              <p class="narrative-text">{{ simulationConfig.event_config.narrative_direction }}</p>
            </div>

            <!-- Hot Topics -->
            <div class="topics-section">
              <span class="box-label">{{ $t('process.step2.step4.hotTopics') }}</span>
              <div class="hot-topics-grid">
                <span v-for="topic in simulationConfig.event_config.hot_topics" :key="topic" class="hot-topic-tag">
                  # {{ topic }}
                </span>
              </div>
            </div>

            <!-- Initial Posts Stream -->
            <div class="initial-posts-section">
              <span class="box-label">{{ $t('process.step2.step4.initialSequence', { count: simulationConfig.event_config.initial_posts.length }) }}</span>
              <div class="posts-timeline">
                <div v-for="(post, idx) in simulationConfig.event_config.initial_posts" :key="idx" class="timeline-item">
                  <div class="timeline-marker"></div>
                  <div class="timeline-content">
                    <div class="post-header">
                      <span class="post-role">{{ post.poster_type }}</span>
                      <span class="post-agent-info">
                        <span class="post-id">{{ $t('process.step2.step3.agentLabel', { id: post.poster_agent_id }) }}</span>
                        <span class="post-username">@{{ getAgentUsername(post.poster_agent_id) }}</span>
                      </span>
                    </div>
                    <p class="post-text">{{ post.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 05: Preparation Complete -->
      <div class="step-card" :class="{ 'active': phase === 4 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">05</span>
            <span class="step-title">{{ $t('process.step2.step5.title') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase >= 4" class="badge processing"><span class="badge-dot"></span>{{ $t('process.common.inProgress') }}</span>
            <span v-else class="badge pending"><span class="badge-dot"></span>{{ $t('process.common.waiting') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/start</p>
          <p class="description">{{ $t('process.step2.step5.description') }}</p>

          <!-- Simulation rounds config - only shown after config generation and rounds calculation -->
          <div v-if="simulationConfig && autoGeneratedRounds" class="rounds-config-section">
            <div class="rounds-header">
              <div class="header-left">
                <span class="section-title">{{ $t('process.step2.step5.roundSettings') }}</span>
                <span class="section-desc">{{ $t('process.step2.step5.roundSettingsDesc', { hours: simulationConfig?.time_config?.total_simulation_hours || '-', min: simulationConfig?.time_config?.minutes_per_round || '-' }) }}</span>
              </div>
              <label class="switch-control">
                <input type="checkbox" v-model="useCustomRounds">
                <span class="switch-track"></span>
                <span class="switch-label">{{ $t('process.step2.step5.custom') }}</span>
              </label>
            </div>

            <Transition name="fade" mode="out-in">
              <div v-if="useCustomRounds" class="rounds-content custom" key="custom">
                <div class="slider-display">
                  <div class="slider-main-value">
                    <span class="val-num">{{ customMaxRounds }}</span>
                    <span class="val-unit">{{ $t('charts.common.rounds').toLowerCase() }}</span>
                  </div>
                  <div class="slider-meta-info">
                    <span>{{ $t('process.step2.step5.estimatedDuration', { n: Math.round(customMaxRounds * (profiles.length || 100) * 0.006) }) }}</span>
                  </div>
                </div>

                <div class="range-wrapper">
                  <input
                    type="range"
                    v-model.number="customMaxRounds"
                    min="10"
                    :max="naturalMaxRounds"
                    step="5"
                    class="minimal-slider"
                    :style="{ '--percent': ((customMaxRounds - 10) / (naturalMaxRounds - 10)) * 100 + '%' }"
                  />
                  <div class="range-marks">
                    <span>10</span>
                    <span
                      class="mark-recommend"
                      :class="{ active: customMaxRounds === 40 }"
                      @click="customMaxRounds = 40"
                      :style="{ position: 'absolute', left: `calc(${(40 - 10) / (naturalMaxRounds - 10) * 100}% - 30px)` }"
                    >{{ $t('process.step2.step5.recommended') }}</span>
                    <span>{{ naturalMaxRounds }}</span>
                  </div>
                </div>
              </div>

              <div v-else class="rounds-content auto" key="auto">
                <div class="auto-info-card">
                  <div class="auto-value">
                    <span class="val-num">{{ autoGeneratedRounds }}</span>
                    <span class="val-unit">{{ $t('charts.common.rounds').toLowerCase() }}</span>
                  </div>
                  <div class="auto-content">
                    <div class="auto-meta-row">
                      <span class="duration-badge">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        {{ $t('process.step2.step5.estimatedDuration', { n: Math.round(autoGeneratedRounds * (profiles.length || 100) * 0.006) }) }}
                      </span>
                    </div>
                    <div class="auto-desc">
                      <p class="highlight-tip" @click="useCustomRounds = true">{{ $t('process.step2.step5.firstTimeTip') }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </Transition>
          </div>

          <div class="action-group dual">
            <button
              class="action-btn secondary ms-btn ms-btn-ghost"
              @click="$emit('go-back')"
            >
              {{ $t('process.step2.step5.backToGraph') }}
            </button>
            <button
              class="action-btn primary ms-btn ms-btn-primary"
              :disabled="phase < 4"
              @click="handleStartSimulation"
            >
              {{ hasRunBefore ? $t('process.step2.step5.resume') : $t('process.step2.step5.start') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile Detail Modal -->
    <Transition name="modal">
      <div v-if="selectedProfile" class="profile-modal-overlay" @click.self="selectedProfile = null">
        <div class="profile-modal">
          <div class="modal-header">
          <div class="modal-header-info">
            <div class="modal-name-row">
              <span class="modal-realname">{{ selectedProfile.username }}</span>
              <span class="modal-username">@{{ selectedProfile.name }}</span>
            </div>
            <span class="modal-profession">{{ selectedProfile.profession }}</span>
          </div>
          <button class="close-btn" @click="selectedProfile = null">×</button>
        </div>
        
        <div class="modal-body">
          <!-- Basic Info -->
          <div class="modal-info-grid">
            <div class="info-item">
              <span class="info-label">{{ $t('process.step2.modal.apparentAge') }}</span>
              <span class="info-value">{{ $t('process.step2.modal.yearsOld', { count: selectedProfile.age || '-' }) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ $t('process.step2.modal.apparentGender') }}</span>
              <span class="info-value">{{ { male: $t('process.step2.modal.male'), female: $t('process.step2.modal.female'), other: $t('process.step2.modal.other') }[selectedProfile.gender] || selectedProfile.gender }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ $t('process.step2.modal.country') }}</span>
              <span class="info-value">{{ selectedProfile.country || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ $t('process.step2.modal.apparentMbti') }}</span>
              <span class="info-value mbti">{{ selectedProfile.mbti || '-' }}</span>
            </div>
          </div>

          <!-- Bio -->
          <div class="modal-section">
            <span class="section-label">{{ $t('process.step2.modal.personaSummary') }}</span>
            <p class="section-bio">{{ selectedProfile.bio || $t('process.step2.step2.noBio') }}</p>
          </div>

          <!-- Related Topics -->
          <div class="modal-section" v-if="selectedProfile.interested_topics?.length">
            <span class="section-label">{{ $t('process.step2.modal.seedTopics') }}</span>
            <div class="topics-grid">
              <span
                v-for="topic in selectedProfile.interested_topics"
                :key="topic"
                class="topic-item"
              >{{ topic }}</span>
            </div>
          </div>

          <!-- Detailed Persona -->
          <div class="modal-section" v-if="selectedProfile.persona">
            <span class="section-label">{{ $t('process.step2.modal.personaDetail') }}</span>

            <!-- Persona Dimension Overview -->
            <div class="persona-dimensions">
              <div class="dimension-card">
                <span class="dim-title">{{ $t('process.step2.modal.fullExperience') }}</span>
                <span class="dim-desc">{{ $t('process.step2.modal.fullExperienceDesc') }}</span>
              </div>
              <div class="dimension-card">
                <span class="dim-title">{{ $t('process.step2.modal.behaviorPattern') }}</span>
                <span class="dim-desc">{{ $t('process.step2.modal.behaviorPatternDesc') }}</span>
              </div>
              <div class="dimension-card">
                <span class="dim-title">{{ $t('process.step2.modal.memoryImprint') }}</span>
                <span class="dim-desc">{{ $t('process.step2.modal.memoryImprintDesc') }}</span>
              </div>
              <div class="dimension-card">
                <span class="dim-title">{{ $t('process.step2.modal.socialNetwork') }}</span>
                <span class="dim-desc">{{ $t('process.step2.modal.socialNetworkDesc') }}</span>
              </div>
            </div>

            <div class="persona-content">
              <p class="section-persona">{{ selectedProfile.persona }}</p>
            </div>
          </div>
        </div>
      </div>
      </div>
    </Transition>

    <!-- Add Agent Modal -->
    <Transition name="modal">
      <div v-if="showAddAgentModal" class="add-agent-overlay" @click.self="showAddAgentModal = false">
        <div class="add-agent-modal">
          <div class="modal-header">
            <span>{{ $t('process.step2.step2.addAgentTitle') }}</span>
            <button class="close-btn" @click="showAddAgentModal = false">×</button>
          </div>
          <div class="modal-body">
            <label>{{ $t('process.step2.step2.addAgentName') }} *
              <input v-model="newAgent.name" class="ms-input" :placeholder="$t('process.step2.step2.addAgentNamePlaceholder')" />
            </label>
            <label>{{ $t('process.step2.step2.addAgentProfession') }}
              <input v-model="newAgent.profession" class="ms-input" :placeholder="$t('process.step2.step2.addAgentProfessionPlaceholder')" />
            </label>
            <label>{{ $t('process.step2.step2.addAgentBio') }}
              <textarea v-model="newAgent.bio" class="ms-input" rows="3" :placeholder="$t('process.step2.step2.addAgentBioPlaceholder')"></textarea>
            </label>
            <label>{{ $t('process.step2.step2.addAgentStance') }}
              <select v-model="newAgent.stance" class="ms-input">
                <option value="neutral">{{ $t('process.step2.step2.stanceNeutral') }}</option>
                <option value="bullish">{{ $t('process.step2.step2.stanceBullish') }}</option>
                <option value="bearish">{{ $t('process.step2.step2.stanceBearish') }}</option>
              </select>
            </label>
            <div v-if="addAgentError" class="add-agent-error">{{ addAgentError }}</div>
          </div>
          <div class="modal-footer">
            <button class="ms-btn ms-btn-ghost ms-btn--sm" @click="showAddAgentModal = false">{{ $t('common.cancel') }}</button>
            <button class="ms-btn ms-btn-primary ms-btn--sm" :disabled="!newAgent.name.trim() || addAgentSaving" @click="submitAddAgent">
              {{ addAgentSaving ? '...' : $t('process.step2.step2.addAgentSubmit') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Bottom Info / Logs -->
    <div class="system-logs" :class="{ collapsed: dashboardCollapsed }">
      <div class="log-header" @click="dashboardCollapsed = !dashboardCollapsed">
        <span class="log-title">{{ $t('process.common.systemDashboard') }} <span class="log-toggle">{{ dashboardCollapsed ? '▲' : '▼' }}</span></span>
        <span class="log-id">{{ simulationId || $t('process.common.noSimulation') }}</span>
      </div>
      <div v-show="!dashboardCollapsed" class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  prepareSimulation,
  getPrepareStatus,
  getSimulationProfilesRealtime,
  getSimulationConfig as _getSimulationConfig,
  getSimulationConfigRealtime,
  retrySimulationConfig,
  getRunStatus
} from '../api/simulation'
import { formatApiError } from '../utils/error-handler'

const { t } = useI18n()

const props = defineProps({
  simulationId: String,  // passed from parent component
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status', 'update-phase'])

// State
const phase = ref(0) // 0: Initializing, 1: Generating Profiles, 2: Generating Config, 3: Complete
const taskId = ref(null)
const prepareProgress = ref(0)
const currentStage = ref('')
const progressMessage = ref('')
const profiles = ref([])
const entityTypes = ref([])
const expectedTotal = ref(null)
const simulationConfig = ref(null)
const selectedProfile = ref(null)
const showProfilesDetail = ref(true)
const profilesExpanded = ref(false)
const agentCardsExpanded = ref(false)
const configError = ref(null)       // Error message when config generation fails
const isConfigRetrying = ref(false) // True while retry is in progress

// ── Add-agent modal ──────────────────────────────────────────────────────
const showAddAgentModal = ref(false)
const addAgentError = ref('')
const addAgentSaving = ref(false)
const newAgent = reactive({ name: '', profession: '', bio: '', stance: 'neutral' })

const contextualErrorHint = computed(() => {
  const msg = (configError.value || '').toLowerCase()
  if (!msg) return t('process.step2.step3.errorHint')
  if (msg.includes('matching entities') || msg.includes('graph is built') || msg.includes('graph_id')) {
    return t('process.step2.step3.hintEntities')
  }
  if (msg.includes('profiles not found') || msg.includes('profile') && msg.includes('prepare')) {
    return t('process.step2.step3.hintProfiles')
  }
  if (msg.includes('timed out') || msg.includes('timeout')) {
    return t('process.step2.step3.hintTimeout')
  }
  if (msg.includes('api key') || msg.includes('quota') || msg.includes('model') || msg.includes('llm')) {
    return t('process.step2.step3.hintLLM')
  }
  return t('process.step2.step3.errorHint')
})

const submitAddAgent = async () => {
  if (!newAgent.name.trim()) return
  addAgentSaving.value = true
  addAgentError.value = ''
  try {
    const token = sessionStorage.getItem('bassira_admin_token') || ''
    const res = await fetch(`/api/simulation/${props.simulationId}/profiles`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({
        name: newAgent.name.trim(),
        username: newAgent.name.trim(),
        profession: newAgent.profession.trim(),
        bio: newAgent.bio.trim(),
        stance: newAgent.stance,
      })
    })
    const d = await res.json()
    if (!d.success) throw new Error(d.error || 'Erreur')
    profiles.value.push({ ...d.data, _isManual: true })
    Object.assign(newAgent, { name: '', profession: '', bio: '', stance: 'neutral' })
    showAddAgentModal.value = false
  } catch (err) {
    addAgentError.value = err instanceof Error ? err.message : String(err)
  } finally {
    addAgentSaving.value = false
  }
}

// Config polling timeout: stop after 90 seconds with no result
const CONFIG_POLL_TIMEOUT_MS = 90000
let configPollStartTime = null

// Log deduplication: track last logged key info
let lastLoggedMessage = ''
let lastLoggedProfileCount = 0
let lastLoggedConfigStage = ''

// Simulation rounds configuration
const useCustomRounds = ref(false) // default: use auto-configured rounds
const customMaxRounds = ref(40)   // default recommended: 40 rounds

// Notify parent whenever phase changes so page title/status stays in sync
watch(phase, (newPhase) => {
  emit('update-phase', newPhase)
}, { immediate: true })

// Watch stage to update phase
watch(currentStage, (newStage) => {
  if (newStage === 'Generating Agent Personas' || newStage === 'generating_profiles') {
    phase.value = 1
  } else if (newStage === 'Generating Simulation Config' || newStage === 'generating_config') {
    phase.value = 2
    // Entering config generation phase, start polling config
    if (!configTimer) {
      addLog('Starting to generate Dual-Platform Simulation Config...')
      startConfigPolling()
    }
  } else if (newStage === 'Preparing Simulation Scripts' || newStage === 'copying_scripts') {
    phase.value = 2 // still in config phase
  }
})

// Cap the auto-recommended round count at 40 (and floor at 30) so a fresh
// run completes in ~10–15 min on Cheap-preset hardware. The Smart-model
// config generator often picks 96h × 45min → 128 rounds, which is fine
// in theory but a long first-run for users dipping a toe in.
// Slider max in custom mode still tracks the *natural* config ceiling so
// power users can dial up beyond 40 when they want a denser sim.
const naturalMaxRounds = computed(() => {
  if (!simulationConfig.value?.time_config) return null
  const totalHours = simulationConfig.value.time_config.total_simulation_hours
  const minutesPerRound = simulationConfig.value.time_config.minutes_per_round
  if (!totalHours || !minutesPerRound) return null
  return Math.max(Math.floor((totalHours * 60) / minutesPerRound), 40)
})

const autoGeneratedRounds = computed(() => {
  const natural = naturalMaxRounds.value
  if (natural === null) return null
  return Math.min(Math.max(natural, 30), 40)
})

// Polling timer
let pollTimer = null
let profilesTimer = null
let configTimer = null

// Computed
const _displayProfiles = computed(() => {
  if (showProfilesDetail.value) {
    return profiles.value
  }
  return profiles.value.slice(0, 6)
})

// Get full profile by agent_id
const getAgentProfile = (agentId) => {
  if (profiles.value && profiles.value.length > agentId && agentId >= 0) {
    return profiles.value[agentId]
  }
  return null
}

// Get username by agent_id
const getAgentUsername = (agentId) => {
  if (profiles.value && profiles.value.length > agentId && agentId >= 0) {
    const profile = profiles.value[agentId]
    return profile?.username || `agent_${agentId}`
  }
  return `agent_${agentId}`
}

// Calculate total related topics across all personas
const totalTopicsCount = computed(() => {
  return profiles.value.reduce((sum, p) => {
    return sum + (p.interested_topics?.length || 0)
  }, 0)
})

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

// Handle start simulation button click
const handleStartSimulation = () => {
  // Build parameters to pass to parent component
  const params = {}

  if (useCustomRounds.value) {
    // User custom rounds, pass max_rounds parameter
    params.maxRounds = customMaxRounds.value
    addLog(`Starting simulation, custom rounds: ${customMaxRounds.value} rounds`)
  } else {
    // User chose to keep auto-generated rounds, no max_rounds parameter passed
    addLog(`Starting simulation, using auto-configured rounds: ${autoGeneratedRounds.value} rounds`)
  }
  
  emit('next-step', params)
}

const _truncateBio = (bio) => {
  if (bio.length > 80) {
    return bio.substring(0, 80) + '...'
  }
  return bio
}

const selectProfile = (profile) => {
  selectedProfile.value = profile
}

// Automatically start simulation preparation
const startPrepareSimulation = async () => {
  if (!props.simulationId) {
    addLog('Error: missing simulationId')
    emit('update-status', 'error')
    return
  }
  
  // Mark first step complete, start second step
  phase.value = 1
  addLog(`Simulation instance created: ${props.simulationId}`)
  addLog('Preparing simulation environment...')
  emit('update-status', 'processing')
  
  try {
    const res = await prepareSimulation({
      simulation_id: props.simulationId,
      use_llm_for_profiles: true,
      parallel_profile_count: 5
    })
    
    if (res.success && res.data) {
      if (res.data.already_prepared) {
        addLog('Detected existing completed preparation, using directly')
        await loadPreparedData()
        return
      }
      
      taskId.value = res.data.task_id
      addLog(`Preparation task started`)
      addLog(`  └─ Task ID: ${res.data.task_id}`)
      
      // Set Expected Total Agents immediately (from prepare API response)
      if (res.data.expected_entities_count) {
        expectedTotal.value = res.data.expected_entities_count
        addLog(`Read ${res.data.expected_entities_count} entities from knowledge graph`)
        if (res.data.entity_types && res.data.entity_types.length > 0) {
          addLog(`  └─ Entity types: ${res.data.entity_types.join(', ')}`)
        }
      }
      
      addLog('Starting to poll preparation progress...')
      // Start polling progress
      startPolling()
      // Start fetching profiles in real-time
      startProfilesPolling()
    } else {
      addLog(`Preparation failed: ${res.error || 'Unknown error'}`)
      emit('update-status', 'error')
    }
  } catch (err) {
    addLog(`Preparation error: ${formatApiError(err, t)}`)
    emit('update-status', 'error')
  }
}

const startPolling = () => {
  pollTimer = setInterval(pollPrepareStatus, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const startProfilesPolling = () => {
  profilesTimer = setInterval(fetchProfilesRealtime, 3000)
}

const stopProfilesPolling = () => {
  if (profilesTimer) {
    clearInterval(profilesTimer)
    profilesTimer = null
  }
}

const pollPrepareStatus = async () => {
  if (!taskId.value && !props.simulationId) return
  
  try {
    const res = await getPrepareStatus({
      task_id: taskId.value,
      simulation_id: props.simulationId
    })
    
    if (res.success && res.data) {
      const data = res.data
      
      // Update progress
      prepareProgress.value = data.progress || 0
      progressMessage.value = data.message || ''
      
      // Parse stage info and output detailed logs
      if (data.progress_detail) {
        currentStage.value = data.progress_detail.current_stage_name || ''
        
        // Output detailed progress log (avoid duplicates)
        const detail = data.progress_detail
        const logKey = `${detail.current_stage}-${detail.current_item}-${detail.total_items}`
        if (logKey !== lastLoggedMessage && detail.item_description) {
          lastLoggedMessage = logKey
          const stageInfo = `[${detail.stage_index}/${detail.total_stages}]`
          if (detail.total_items > 0) {
            addLog(`${stageInfo} ${detail.current_stage_name}: ${detail.current_item}/${detail.total_items} - ${detail.item_description}`)
          } else {
            addLog(`${stageInfo} ${detail.current_stage_name}: ${detail.item_description}`)
          }
        }
      } else if (data.message) {
        // Extract stage from message
        const match = data.message.match(/\[(\d+)\/(\d+)\]\s*([^:]+)/)
        if (match) {
          currentStage.value = match[3].trim()
        }
        // Output message log (avoid duplicates)
        if (data.message !== lastLoggedMessage) {
          lastLoggedMessage = data.message
          addLog(data.message)
        }
      }
      
      // Check if completed
      if (data.status === 'completed' || data.status === 'ready' || data.already_prepared) {
        addLog('✓ Preparation completed')
        stopPolling()
        stopProfilesPolling()
        await loadPreparedData()
      } else if (data.status === 'failed') {
        addLog(`✗ Preparation failed: ${data.error || 'Unknown error'}`)
        stopPolling()
        stopProfilesPolling()
      }
    }
  } catch (err) {
    console.warn('Polling status failed:', err)
  }
}

const fetchProfilesRealtime = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId, 'reddit')
    
    if (res.success && res.data) {
      const _prevCount = profiles.value.length
      profiles.value = res.data.profiles || []
      // Only update when API returns valid value, avoid overwriting existing valid value
      if (res.data.total_expected) {
        expectedTotal.value = res.data.total_expected
      }
      
      // Extract entity types
      const types = new Set()
      profiles.value.forEach(p => {
        if (p.entity_type) types.add(p.entity_type)
      })
      entityTypes.value = Array.from(types)
      
      // Output profile generation progress log (only when count changes)
      const currentCount = profiles.value.length
      if (currentCount > 0 && currentCount !== lastLoggedProfileCount) {
        lastLoggedProfileCount = currentCount
        const total = expectedTotal.value || '?'
        const latestProfile = profiles.value[currentCount - 1]
        const profileName = latestProfile?.name || latestProfile?.username || `Agent_${currentCount}`
        if (currentCount === 1) {
          addLog(`Starting to generate agent personas...`)
        }
        addLog(`→ Agent persona ${currentCount}/${total}: ${profileName} (${latestProfile?.profession || 'Unknown Profession'})`)
        
        // If all generated
        if (expectedTotal.value && currentCount >= expectedTotal.value) {
          addLog(`✓ All ${currentCount} agent personas generated`)
        }
      }
    }
  } catch (err) {
    console.warn('Failed to get profiles:', err)
  }
}

// Config polling
const startConfigPolling = () => {
  configError.value = null
  configPollStartTime = Date.now()
  configTimer = setInterval(fetchConfigRealtime, 2000)
}

const stopConfigPolling = () => {
  if (configTimer) {
    clearInterval(configTimer)
    configTimer = null
  }
}

const fetchConfigRealtime = async () => {
  if (!props.simulationId) return

  // Client-side timeout: give up after CONFIG_POLL_TIMEOUT_MS
  if (configPollStartTime && Date.now() - configPollStartTime > CONFIG_POLL_TIMEOUT_MS) {
    stopConfigPolling()
    configError.value = 'Config generation timed out after 90 seconds. The LLM may be unresponsive or overloaded.'
    addLog('✗ Config generation timed out (90s). Use "Retry Config" to try again.')
    return
  }

  try {
    const res = await getSimulationConfigRealtime(props.simulationId)

    if (res.success && res.data) {
      const data = res.data

      // Backend reported a generation failure
      if (data.config_error || data.status === 'failed') {
        stopConfigPolling()
        const reason = data.config_error || 'Generation failed — check backend logs and graph state'
        configError.value = reason
        addLog(`✗ Config generation failed: ${reason}`)
        return
      }

      // Output config generation stage log (avoid duplicates)
      if (data.generation_stage && data.generation_stage !== lastLoggedConfigStage) {
        lastLoggedConfigStage = data.generation_stage
        if (data.generation_stage === 'generating_profiles') {
          addLog('Generating agent persona configuration...')
        } else if (data.generation_stage === 'generating_config') {
          addLog('Calling LLM to generate simulation configuration parameters...')
        }
      }

      // If config has been generated
      if (data.config_generated && data.config) {
        simulationConfig.value = data.config
        addLog('✓ Simulation configuration generated')

        // Show detailed config summary
        if (data.summary) {
          addLog(`  ├─ Agent count: ${data.summary.total_agents}`)
          addLog(`  ├─ Simulation duration: ${data.summary.simulation_hours} hours`)
          addLog(`  ├─ Initial posts: ${data.summary.initial_posts_count}`)
          addLog(`  ├─ Hot topics: ${data.summary.hot_topics_count}`)
          addLog(`  └─ Platform config: Twitter ${data.summary.has_twitter_config ? '✓' : '✗'}, Reddit ${data.summary.has_reddit_config ? '✓' : '✗'}`)
        }

        // Show time configuration details
        if (data.config.time_config) {
          const tc = data.config.time_config
          addLog(`Time config: ${tc.minutes_per_round} minutes per round, ${Math.floor((tc.total_simulation_hours * 60) / tc.minutes_per_round)} rounds total`)
        }

        // Show event configuration
        if (data.config.event_config?.narrative_direction) {
          const narrative = data.config.event_config.narrative_direction
          addLog(`Narrative direction: ${narrative.length > 50 ? narrative.substring(0, 50) + '...' : narrative}`)
        }

        stopConfigPolling()
        phase.value = 4
        addLog('✓ Environment setup complete, ready to start simulation')
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('Failed to get config:', err)
  }
}

const handleConfigRetry = async () => {
  if (!props.simulationId || isConfigRetrying.value) return
  isConfigRetrying.value = true
  configError.value = null
  lastLoggedConfigStage = ''
  addLog('Retrying config generation...')

  try {
    const res = await retrySimulationConfig(props.simulationId)
    if (res.success) {
      addLog('Config retry started — waiting for LLM...')
      startConfigPolling()
    } else {
      configError.value = res.error || 'Retry failed — check backend logs'
      addLog(`✗ Retry failed: ${res.error || 'unknown error'}`)
    }
  } catch (err) {
    // US-007: surface a localised, error_code-aware message rather than the raw
    // English `error` string so the operator sees a helpful translation in fr/ar.
    const localised = formatApiError(err, t)
    configError.value = localised
    addLog(`✗ Retry error: ${localised}`)
  } finally {
    isConfigRetrying.value = false
  }
}

const loadPreparedData = async () => {
  phase.value = 2
  addLog('Loading existing configuration data...')

  // Fetch profiles one last time
  await fetchProfilesRealtime()
  addLog(`Loaded ${profiles.value.length} agent personas`)

  // Get config (using real-time API)
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    if (res.success && res.data) {
      if (res.data.config_generated && res.data.config) {
        simulationConfig.value = res.data.config
        addLog('✓ Simulation configuration loaded successfully')

        // Show detailed config summary
        if (res.data.summary) {
          addLog(`  ├─ Agent count: ${res.data.summary.total_agents}`)
          addLog(`  ├─ Simulation duration: ${res.data.summary.simulation_hours} hours`)
          addLog(`  └─ Initial posts: ${res.data.summary.initial_posts_count}`)
        }
        
        addLog('✓ Environment setup complete, ready to start simulation')
        phase.value = 4
        emit('update-status', 'completed')
      } else {
        // Config not yet generated, start polling
        addLog('Config generating, starting to poll...')
        startConfigPolling()
      }
    }
  } catch (err) {
    addLog(`Failed to load configuration: ${formatApiError(err, t)}`)
    emit('update-status', 'error')
  }
}

// Scroll log to bottom
const logContent = ref(null)
const dashboardCollapsed = ref(true)
const hasRunBefore = ref(false)

const copyValue = (val) => {
  if (!val) return
  navigator.clipboard.writeText(val)
}
watch(() => props.systemLogs?.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})

onMounted(async () => {
  if (props.simulationId) {
    // Check if this simulation has run before
    try {
      const res = await getRunStatus(props.simulationId)
      if (res.success && res.data && res.data.current_round > 0) {
        hasRunBefore.value = true
      }
    } catch (_err) {
      // no run state — fresh simulation
    }

    addLog('Step 2 Agent Setup Initializing')
    startPrepareSimulation()
  }
})

onUnmounted(() => {
  stopPolling()
  stopProfilesPolling()
  stopConfigPolling()
})
</script>

<style scoped>
.env-setup-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--wi-bg);
  font-family: var(--wi-font-body);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}

/* Step Card */
.step-card {
  background: var(--wi-surface);
  padding: var(--wi-space-md);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-md);
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
  position: relative;
}

.step-card.active {
  border-inline-start: 4px solid var(--wi-primary-container);
  box-shadow: var(--wi-shadow-ambient);
}

.step-card.completed {
  border-color: var(--wi-secondary-container);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 11px;
}

.step-num {
  font-family: var(--ms-font-mono);
  font-size: 20px;
  font-weight: 700;
  color: var(--wi-outline-variant);
}

.step-card.active .step-num,
.step-card.completed .step-num {
  color: var(--wi-on-surface);
}

.step-title {
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.005em;
  color: var(--wi-on-surface);
}

/* .badge + .badge-dot + @keyframes badge-pulse factorisés dans styles/components.css.
   Variants locaux de Step2 ci-dessous (palette --wi-* warm intelligence). */
.badge.success { background: var(--wi-secondary-container); color: var(--wi-on-secondary-container); }
.badge.processing { background: var(--wi-primary-container); color: var(--wi-on-primary-container); }
.badge.processing .badge-dot { animation: badge-pulse 1s infinite; }
.badge.pending { background: var(--wi-surface-container-low); color: var(--wi-on-surface-variant); }
.badge.accent { background: var(--wi-primary-container); color: var(--wi-on-primary-container); }
.badge.error { background: var(--wi-error-container); color: var(--wi-on-error-container); }

.step-card.error { border-color: rgba(255,68,68,0.3); }

.config-error-panel {
  border: 2px solid var(--ms-rose);
  background: rgba(255,68,68,0.04);
  padding: 16px;
  margin-bottom: 16px;
}

.config-error-title {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: var(--ms-rose);
  margin-bottom: 8px;
}

.config-error-msg {
  font-size: 13px;
  color: rgba(10,10,10,0.7);
  margin-bottom: 8px;
  word-break: break-word;
}

.config-error-hint {
  font-size: 12px;
  color: rgba(10,10,10,0.5);
  margin-bottom: 14px;
  line-height: 1.6;
}

.config-error-hint code {
  font-family: var(--ms-font-mono);
  background: rgba(10,10,10,0.06);
  padding: 1px 4px;
  font-size: 11px;
}

.retry-config-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  background: var(--ms-rose);
  color: var(--ms-bg-elevated);
  border: none;
  font-family: var(--ms-font-mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-config-btn:hover:not(:disabled) { background: var(--ms-status-danger-strong); }
.retry-config-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* .loading-spinner-small factorisé dans styles/components.css.
   On ne garde ici qu'un override de couleur pour le bouton retry sur fond rouge. */
.retry-config-btn .loading-spinner-small {
  border-color: rgba(255, 255, 255, 0.3);
  border-top-color: var(--ms-bg-elevated);
}


.card-content {
  /* No extra padding - uses step-card's padding */
}

.api-note {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  margin-bottom: 8px;
  opacity: 0.8;
}

.description {
  font-family: var(--wi-font-body);
  font-size: 13px;
  color: var(--wi-on-surface-variant);
  line-height: 1.5;
  margin-bottom: 16px;
}

/* Action Section */
.action-section {
  margin-top: 16px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-body);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.01em;
  border: none;
  cursor: pointer;
  transition: all 0.2s var(--ms-ease);
}

.action-btn.primary {
  background: var(--wi-on-primary-container);
  color: var(--wi-bg);
  box-shadow: var(--wi-shadow-md);
}

.action-btn.primary:hover:not(:disabled) {
  background: var(--wi-primary);
  box-shadow: var(--wi-shadow-lg);
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: var(--wi-surface-container-low);
  color: var(--wi-on-surface);
  border: 1px solid var(--wi-outline-variant);
}

.action-btn.secondary:hover:not(:disabled) {
  background: var(--wi-surface-container);
  border-color: var(--wi-outline);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-group {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.action-group.dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.action-group.dual .action-btn {
  width: 100%;
}

/* Info Card */
.info-card {
  background: var(--wi-surface-container-low);
  padding: 16px;
  margin-top: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed rgba(10,10,10,0.12);
  cursor: pointer;
  user-select: none;
}

.info-row:hover .info-value.copyable {
  color: var(--ms-text);
  text-decoration: underline;
}

.info-row:active .info-value.copyable {
  color: var(--ms-mint);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: rgba(10,10,10,0.5);
  text-transform: uppercase;
  letter-spacing: 3px;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
}

.info-value.mono {
  font-family: var(--ms-font-mono);
  font-size: 12px;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 11px;
  background: var(--wi-surface-container-low);
  padding: 16px;
}

/* .stat-card / .stat-value / .stat-label factorisés dans styles/components.css */

/* Profiles Preview */
.profiles-preview {
  margin-top: 22px;
  border-top: 2px solid rgba(10,10,10,0.08);
  padding-top: 16px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-title {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 600;
  color: rgba(10,10,10,0.5);
  text-transform: uppercase;
  letter-spacing: 3px;
}

.profiles-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.profiles-toggle {
  display: block;
  width: 100%;
  margin-top: 10px;
  padding: 8px;
  background: transparent;
  border: 2px solid rgba(10,10,10,0.08);
  font-family: var(--font-mono, 'Space Mono', monospace);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: rgba(10,10,10,0.4);
  cursor: pointer;
  transition: all 0.15s;
}
.profiles-toggle:hover {
  border-color: rgba(10,10,10,0.2);
  color: rgba(10,10,10,0.7);
}

.profile-card {
  background: var(--ms-bg-elevated);
  border: 2px solid rgba(10,10,10,0.08);
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 0;
  overflow: hidden;
}

.profile-card:hover {
  border-color: var(--ms-orange);
  background: var(--ms-bg-elevated);
}

.profile-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
  overflow: hidden;
}

.profile-header > * {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.profile-realname {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 700;
  color: var(--ms-text);
}

.profile-username {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: rgba(10,10,10,0.4);
}

.profile-meta {
  margin-bottom: 8px;
}

.profile-profession {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: rgba(10,10,10,0.5);
  background: var(--wi-surface-container-low);
  padding: 2px 8px;
}

.profile-bio {
  font-size: 12px;
  color: rgba(10,10,10,0.5);
  line-height: 1.6;
  margin: 0 0 10px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.profile-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.topic-tag {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  color: var(--ms-orange);
  background: rgba(255,107,26,0.1);
  padding: 2px 8px;
}

.topic-more {
  font-size: 10px;
  color: rgba(10,10,10,0.4);
  padding: 2px 6px;
}

/* Config Preview */
/* Config Detail Panel */
.config-detail-panel {
  margin-top: 16px;
}

.config-block {
  margin-top: 16px;
  border-top: 2px solid rgba(10,10,10,0.08);
  padding-top: 12px;
}

.config-block:first-child {
  margin-top: 0;
  border-top: none;
  padding-top: 0;
}

.config-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.config-block-title {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 600;
  color: rgba(10,10,10,0.5);
  text-transform: uppercase;
  letter-spacing: 3px;
}

.config-block-badge {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  background: var(--wi-surface-container-low);
  color: rgba(10,10,10,0.5);
  padding: 2px 8px;
}

/* Config Grid */
.config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.config-item {
  background: var(--wi-surface-container-low);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-item-label {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: rgba(10,10,10,0.4);
  text-transform: uppercase;
  letter-spacing: 3px;
}

.config-item-value {
  font-family: var(--ms-font-mono);
  font-size: 16px;
  font-weight: 600;
  color: var(--ms-text);
}

/* Time Periods */
.time-periods {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.period-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 8px 12px;
  background: var(--wi-surface-container-low);
}

.period-label {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  font-weight: 500;
  color: rgba(10,10,10,0.5);
  min-width: 70px;
}

.period-hours {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: rgba(10,10,10,0.5);
  flex: 1;
}

.period-multiplier {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--ms-orange);
  background: rgba(255,107,26,0.1);
  padding: 2px 6px;
}

/* Agents Cards */
.agents-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}


.agent-card {
  background: var(--wi-surface-container-low);
  border: 2px solid rgba(10,10,10,0.08);
  padding: 14px;
  transition: all 0.2s ease;
  min-width: 0;
  overflow: hidden;
}

.agent-card:hover {
  border-color: var(--ms-orange);
  background: var(--ms-bg-elevated);
}

/* Agent Card Header */
.agent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 2px solid rgba(10,10,10,0.08);
}

.agent-identity {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-id {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.4);
}

.agent-name {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--ms-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-tags {
  display: flex;
  gap: 6px;
}

.agent-type {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.5);
  background: var(--wi-surface-container-low);
  padding: 2px 8px;
}

.agent-stance {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 3px;
  padding: 2px 8px;
}

.stance-neutral {
  background: var(--wi-surface-container-low);
  color: rgba(10,10,10,0.5);
}

.stance-supportive {
  background: rgba(67,193,101,0.1);
  color: var(--ms-mint);
}

.stance-opposing {
  background: rgba(255,68,68,0.1);
  color: var(--ms-rose);
}

.stance-observer {
  background: rgba(255,179,71,0.1);
  color: var(--ms-peach);
}

/* Agent Profile Info */
.agent-profile-info {
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: flex-start;
}

.profile-profession-tag,
.profile-country-tag,
.profile-mbti-tag {
  font-family: var(--ms-font-mono);
  font-size: 0.7rem;
  padding: 2px 8px;
  border: 2px solid rgba(10,10,10,0.08);
  color: rgba(10,10,10,0.5);
  letter-spacing: 0.5px;
}

.profile-profession-tag { border-color: var(--ms-orange); color: var(--ms-orange); }
.profile-mbti-tag { border-color: var(--ms-mint); color: var(--ms-mint); }

.profile-bio-snippet {
  width: 100%;
  font-size: 0.75rem;
  color: rgba(10,10,10,0.4);
  line-height: 1.4;
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Agent Timeline */
.agent-timeline {
  margin-bottom: 14px;
}

.timeline-label {
  display: block;
  font-family: var(--ms-font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.4);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 3px;
}

.mini-timeline {
  display: flex;
  gap: 2px;
  height: 16px;
  background: var(--wi-surface-container-low);
  padding: 3px;
}

.timeline-hour {
  flex: 1;
  background: rgba(10,10,10,0.08);
  transition: all 0.2s;
}

.timeline-hour.active {
  background: var(--ms-orange);
}

.timeline-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-family: var(--ms-font-mono);
  font-size: 9px;
  color: rgba(10,10,10,0.4);
}

/* Agent Params */
.agent-params {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.param-group {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.param-item .param-label {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.4);
}

.param-item .param-value {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  font-weight: 600;
  color: rgba(10,10,10,0.5);
}

.param-value.with-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mini-bar {
  height: 4px;
  background: var(--ms-orange);
  min-width: 4px;
  max-width: 40px;
}

.param-value.positive {
  color: var(--ms-mint);
}

.param-value.negative {
  color: var(--ms-rose);
}

.param-value.neutral {
  color: rgba(10,10,10,0.5);
}

.param-value.highlight {
  color: var(--ms-orange);
}

/* Platforms Grid */
.platforms-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.platform-card {
  background: var(--wi-surface-container-low);
  padding: 14px;
  border: 2px solid rgba(10,10,10,0.08);
}

.platform-card-header {
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 2px solid rgba(10,10,10,0.08);
}

.platform-name {
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 600;
  color: rgba(10,10,10,0.7);
}

.platform-params {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-label {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: rgba(10,10,10,0.5);
}

.param-value {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--ms-text);
}

/* Reasoning Content */
.reasoning-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reasoning-item {
  padding: 12px 14px;
  background: var(--wi-surface-container-low);
}

.reasoning-text {
  font-size: 13px;
  color: rgba(10,10,10,0.5);
  line-height: 1.7;
  margin: 0;
}

/* Profile Modal */
.profile-modal-overlay {
  position: fixed;
  top: 0;
  inset-inline-start: 0;
  inset-inline-end: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.profile-modal {
  background: var(--ms-bg-elevated);
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 2px solid rgba(10,10,10,0.12);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 22px;
  background: var(--ms-bg-elevated);
  border-bottom: 2px solid rgba(10,10,10,0.08);
}

.modal-header-info {
  flex: 1;
}

.modal-name-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.modal-realname {
  font-family: var(--wi-font-heading);
  font-size: 20px;
  font-weight: 700;
  color: var(--ms-text);
}

.modal-username {
  font-family: var(--ms-font-mono);
  font-size: 13px;
  color: rgba(10,10,10,0.4);
}

.modal-profession {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: rgba(10,10,10,0.5);
  background: var(--wi-surface-container-low);
  padding: 4px 10px;
  display: inline-block;
  font-weight: 500;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  color: rgba(10,10,10,0.4);
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: color 0.2s;
  padding: 0;
}

.close-btn:hover {
  color: rgba(10,10,10,0.7);
}

.modal-body {
  padding: 22px;
  overflow-y: auto;
  flex: 1;
}

/* Basic Info Grid */
.modal-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px 16px;
  margin-bottom: 32px;
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: rgba(10,10,10,0.4);
  text-transform: uppercase;
  letter-spacing: 3px;
  font-weight: 600;
}

.info-value {
  font-size: 15px;
  font-weight: 600;
  color: rgba(10,10,10,0.7);
}

.info-value.mbti {
  font-family: var(--ms-font-mono);
  color: var(--ms-orange);
}

/* Section Area */
.modal-section {
  margin-bottom: 28px;
}

.section-label {
  display: block;
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 600;
  color: rgba(10,10,10,0.4);
  text-transform: uppercase;
  letter-spacing: 3px;
  margin-bottom: 12px;
}

.section-bio {
  font-size: 14px;
  color: rgba(10,10,10,0.7);
  line-height: 1.6;
  margin: 0;
  padding: 16px;
  background: var(--wi-surface-container-low);
  border-inline-start: 3px solid rgba(10,10,10,0.12);
}

/* Topic Tags */
.topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-item {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--ms-orange);
  background: rgba(255,107,26,0.1);
  padding: 4px 10px;
  transition: all 0.2s;
  border: none;
}

.topic-item:hover {
  background: rgba(255,107,26,0.2);
  color: var(--ms-orange);
}

/* Detailed Persona */
.persona-dimensions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.dimension-card {
  background: var(--wi-surface-container-low);
  padding: 12px;
  border-inline-start: 3px solid rgba(10,10,10,0.12);
  transition: all 0.2s;
}

.dimension-card:hover {
  background: rgba(10,10,10,0.05);
  border-inline-start-color: var(--ms-orange);
}

.dim-title {
  display: block;
  font-family: var(--wi-font-heading);
  font-size: 12px;
  font-weight: 700;
  color: rgba(10,10,10,0.7);
  margin-bottom: 4px;
}

.dim-desc {
  display: block;
  font-size: 10px;
  color: rgba(10,10,10,0.4);
  line-height: 1.4;
}

.persona-content {
  max-height: none;
  overflow: visible;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
}

.persona-content::-webkit-scrollbar {
  width: 4px;
}

.persona-content::-webkit-scrollbar-thumb {
  background: rgba(10,10,10,0.12);
}

.section-persona {
  font-size: 13px;
  color: rgba(10,10,10,0.5);
  line-height: 1.8;
  margin: 0;
  text-align: justify;
}

/* System Logs */
.system-logs {
  background: var(--ms-text);
  color: rgba(250,250,250,0.8);
  padding: 16px;
  font-family: var(--ms-font-mono);
  border-top: 2px solid rgba(10,10,10,0.12);
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid rgba(250,250,250,0.1);
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: rgba(250,250,250,0.4);
  cursor: pointer;
  user-select: none;
}

.system-logs.collapsed .log-header {
  border-bottom: none;
  padding-bottom: 0;
  margin-bottom: 0;
}

.log-toggle {
  font-size: 8px;
  opacity: 0.5;
  margin-inline-start: 4px;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 80px; /* Approx 4 lines visible */
  overflow-y: auto;
  padding-inline-end: 4px;
}

.log-content::-webkit-scrollbar {
  width: 4px;
}

.log-content::-webkit-scrollbar-thumb {
  background: rgba(250,250,250,0.15);
}

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-time {
  color: rgba(250,250,250,0.3);
  min-width: 75px;
}

.log-msg {
  color: rgba(250,250,250,0.7);
  word-break: break-all;
}

/* .spinner-sm + @keyframes spin factorisés dans styles/components.css.
   Override local : version 16px (vs 12px par défaut) sur cet écran. */
.orchestration .spinner-sm,
.env-setup .spinner-sm {
  width: 16px;
  height: 16px;
  border-color: rgba(10, 10, 10, 0.08);
  border-top-color: var(--ms-orange);
}

/* Orchestration Content */
.orchestration-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 16px;
}

.box-label {
  display: block;
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 600;
  color: rgba(10,10,10,0.5);
  text-transform: uppercase;
  letter-spacing: 3px;
  margin-bottom: 11px;
}

.narrative-box {
  background: var(--ms-bg-elevated);
  padding: 22px;
  border: 2px solid rgba(10,10,10,0.08);
  transition: all 0.3s ease;
}

.narrative-box .box-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(10,10,10,0.5);
  font-family: var(--ms-font-mono);
  font-size: 13px;
  letter-spacing: 3px;
  margin-bottom: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.special-icon {
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.narrative-box:hover .special-icon {
  transform: rotate(180deg);
}

.narrative-text {
  font-size: 14px;
  color: rgba(10,10,10,0.7);
  line-height: 1.8;
  margin: 0;
  text-align: justify;
  letter-spacing: 0.01em;
}

.topics-section {
  background: var(--ms-bg-elevated);
}

.hot-topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hot-topic-tag {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--ms-orange);
  background: rgba(255,107,26,0.1);
  padding: 4px 10px;
  font-weight: 500;
}

.hot-topic-more {
  font-size: 11px;
  color: rgba(10,10,10,0.4);
  padding: 4px 6px;
}

.initial-posts-section {
  border-top: 2px solid rgba(10,10,10,0.08);
  padding-top: 16px;
}

.posts-timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-inline-start: 8px;
  border-inline-start: 2px solid rgba(10,10,10,0.08);
  margin-top: 12px;
}

.timeline-item {
  position: relative;
  padding-inline-start: 20px;
}

.timeline-marker {
  position: absolute;
  inset-inline-start: 0;
  top: 14px;
  width: 12px;
  height: 2px;
  background: rgba(10,10,10,0.12);
}

.timeline-content {
  background: var(--wi-surface-container-low);
  padding: 12px;
  border: 2px solid rgba(10,10,10,0.08);
}

.post-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.post-role {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 700;
  color: rgba(10,10,10,0.7);
  text-transform: uppercase;
  letter-spacing: 3px;
}

.post-agent-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.post-id,
.post-username {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.5);
  line-height: 1;
  vertical-align: baseline;
}

.post-username {
  margin-inline-end: 6px;
}

.post-text {
  font-size: 12px;
  color: rgba(10,10,10,0.5);
  line-height: 1.5;
  margin: 0;
}

/* Simulation Rounds Configuration Styles */
.rounds-config-section {
  margin: 22px 0;
  padding-top: 22px;
  border-top: 2px solid rgba(10,10,10,0.08);
}

.rounds-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--ms-text);
}

.section-desc {
  font-size: 12px;
  color: rgba(10,10,10,0.4);
}

.desc-highlight {
  font-family: var(--ms-font-mono);
  font-weight: 600;
  color: var(--ms-text);
  background: var(--wi-surface-container-low);
  padding: 1px 6px;
  margin: 0 2px;
}

/* Switch Control */
.switch-control {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  transition: background 0.2s;
}

.switch-control:hover {
  background: var(--wi-surface-container-low);
}

.switch-control input {
  display: none;
}

.switch-track {
  width: 36px;
  height: 20px;
  background: rgba(10,10,10,0.12);
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.switch-track::after {
  content: '';
  position: absolute;
  inset-inline-start: 2px;
  top: 2px;
  width: 16px;
  height: 16px;
  background: var(--ms-bg-elevated);
  transition: transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.switch-control input:checked + .switch-track {
  background: var(--ms-text);
}

.switch-control input:checked + .switch-track::after {
  transform: translateX(16px);
}

.switch-label {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  font-weight: 500;
  color: rgba(10,10,10,0.5);
}

.switch-control input:checked ~ .switch-label {
  color: var(--ms-text);
}

/* Slider Content */
.rounds-content {
  animation: fadeIn 0.3s ease;
}

.slider-display {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}

.slider-main-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.val-num {
  font-family: var(--ms-font-mono);
  font-size: 24px;
  font-weight: 700;
  color: var(--ms-text);
}

.val-unit {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: rgba(10,10,10,0.5);
  font-weight: 500;
}

.slider-meta-info {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: rgba(10,10,10,0.5);
  background: var(--wi-surface-container-low);
  padding: 4px 8px;
}

.range-wrapper {
  position: relative;
  padding: 0 2px;
}

.minimal-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  background: rgba(10,10,10,0.08);
  outline: none;
  background-image: linear-gradient(var(--ms-text), var(--ms-text));
  background-size: var(--percent, 0%) 100%;
  background-repeat: no-repeat;
  cursor: pointer;
}

.minimal-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: var(--ms-bg-elevated);
  border: 2px solid var(--ms-text);
  cursor: pointer;
  transition: transform 0.1s;
  margin-top: -6px; /* Center thumb */
}

.minimal-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.minimal-slider::-webkit-slider-runnable-track {
  height: 4px;
}

.range-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-family: var(--ms-font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.4);
  position: relative;
}

.mark-recommend {
  cursor: pointer;
  transition: color 0.2s;
  position: relative;
}

.mark-recommend:hover {
  color: var(--ms-text);
}

.mark-recommend.active {
  color: var(--ms-text);
  font-weight: 600;
}

.mark-recommend::after {
  content: '';
  position: absolute;
  top: -12px;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  width: 1px;
  height: 4px;
  background: rgba(10,10,10,0.12);
}

/* Auto Info */
.auto-info-card {
  display: flex;
  align-items: center;
  gap: 22px;
  background: var(--wi-surface-container-low);
  padding: 16px 22px;
}

.auto-value {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 4px;
  padding-inline-end: 22px;
  border-inline-end: 2px solid rgba(10,10,10,0.08);
}

.auto-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
}

.auto-meta-row {
  display: flex;
  align-items: center;
}

.duration-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 500;
  color: rgba(10,10,10,0.5);
  background: var(--ms-bg-elevated);
  border: 2px solid rgba(10,10,10,0.08);
  padding: 3px 8px;
}

.auto-desc {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.auto-desc p {
  margin: 0;
  font-size: 13px;
  color: rgba(10,10,10,0.5);
  line-height: 1.5;
}

/* Spécificité 0,2,1 (.auto-desc p.highlight-tip) > 0,1,1 (.auto-desc p),
   évite l'usage de !important (US-016). */
.auto-desc p.highlight-tip {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ms-text);
  font-weight: 500;
  cursor: pointer;
}

.auto-desc p.highlight-tip:hover {
  text-decoration: underline;
}

/* @keyframes fadeIn factorisé dans styles/components.css */

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Modal Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .profile-modal {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-leave-active .profile-modal {
  transition: all 0.3s ease-in;
}

.modal-enter-from .profile-modal,
.modal-leave-to .profile-modal {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

/* ── Add-agent button & modal ─────────────────────────────────────────── */
.add-agent-btn {
  margin-top: 0.5rem;
}

.add-agent-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.add-agent-modal {
  background: var(--ms-surface);
  border-radius: var(--ms-radius-lg);
  padding: 1.5rem;
  width: min(480px, 90vw);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.add-agent-modal .modal-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.add-agent-modal .modal-body label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.82rem;
  font-weight: 500;
}

.add-agent-modal .modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.add-agent-error {
  color: var(--ms-status-danger, #ef4444);
  font-size: 0.8rem;
}

.profile-manual-badge {
  font-size: 0.7rem;
  color: var(--ms-text-muted, #9ca3af);
  margin-left: 0.25rem;
  cursor: default;
  user-select: none;
}
</style>
