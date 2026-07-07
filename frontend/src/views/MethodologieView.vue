<template>
  <main class="mt-root" :aria-label="$t('methodologie.title')">
    <!-- Hero -->
    <header class="mt-hero">
      <p class="mt-kicker">{{ $t('methodologie.kicker') }}</p>
      <h1 class="mt-title">{{ $t('methodologie.title') }}</h1>
      <p class="mt-sub">{{ $t('methodologie.sub') }}</p>
    </header>

    <!-- Pipeline -->
    <section class="mt-section" :aria-label="$t('methodologie.pipeline.title')">
      <h2 class="mt-h2">{{ $t('methodologie.pipeline.title') }}</h2>
      <ol class="mt-pipeline">
        <li v-for="n in 5" :key="n" class="mt-step">
          <span class="mt-step-num ms-mono" aria-hidden="true">{{ n }}</span>
          <p class="mt-step-body">{{ $t(`methodologie.pipeline.step${n}`) }}</p>
        </li>
      </ol>
    </section>

    <!-- Ce que vous obtenez -->
    <section class="mt-section" :aria-label="$t('methodologie.get.title')">
      <h2 class="mt-h2">{{ $t('methodologie.get.title') }}</h2>
      <div class="mt-grid">
        <article v-for="n in 4" :key="n" class="mt-card">
          <h3 class="mt-card-title">{{ $t(`methodologie.get.c${n}t`) }}</h3>
          <p class="mt-card-body">{{ $t(`methodologie.get.c${n}b`) }}</p>
        </article>
      </div>
    </section>

    <!-- Ce que Bassira ne fait pas -->
    <section class="mt-section" :aria-label="$t('methodologie.not.title')">
      <h2 class="mt-h2">{{ $t('methodologie.not.title') }}</h2>
      <div class="mt-grid mt-grid--3">
        <article v-for="n in 3" :key="n" class="mt-card mt-card--not">
          <h3 class="mt-card-title">{{ $t(`methodologie.not.n${n}t`) }}</h3>
          <p class="mt-card-body">{{ $t(`methodologie.not.n${n}b`) }}</p>
        </article>
      </div>
    </section>

    <!-- Ancrage optionnel -->
    <section class="mt-section" :aria-label="$t('methodologie.anchor.title')">
      <article class="mt-card mt-card--wide">
        <h2 class="mt-card-title">{{ $t('methodologie.anchor.title') }}</h2>
        <p class="mt-card-body">{{ $t('methodologie.anchor.body') }}</p>
      </article>
    </section>

    <!-- CTA -->
    <section class="mt-cta">
      <h2 class="mt-h2">{{ $t('methodologie.cta.title') }}</h2>
      <router-link to="/devis" class="mt-cta-btn">
        {{ $t('methodologie.cta.button') }}
      </router-link>
    </section>
  </main>
</template>

<script setup>
/**
 * /methodologie (alias /calibration) — page publique de crédibilité.
 * Remplace l'ancienne CalibrationView (US-201, ADR-002) : plus aucun claim
 * chiffré non étayé ; la transparence sur la méthode ET ses limites est
 * l'argument commercial. Contenu 100 % i18n (methodologie.*), zéro appel API.
 */
</script>

<style scoped>
.mt-root {
  min-height: 100vh;
  background: var(--wi-bg, #FAF7F2);
  color: var(--wi-text, #241915);
  padding-block: 64px 96px;
  padding-inline: clamp(20px, 6vw, 96px);
}

.mt-hero { max-width: 780px; margin-inline: auto; text-align: center; }
.mt-kicker {
  font-family: var(--wi-font-mono, 'JetBrains Mono', monospace);
  font-size: 0.8rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--wi-primary, #FF8551);
}
.mt-title {
  font-family: var(--wi-font-title, 'Outfit', sans-serif);
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  line-height: 1.15;
  margin-block: 12px 16px;
}
.mt-sub { font-size: 1.05rem; opacity: 0.82; }

.mt-section { max-width: 980px; margin: 56px auto 0; }
.mt-h2 {
  font-family: var(--wi-font-title, 'Outfit', sans-serif);
  font-size: 1.4rem;
  margin-block-end: 20px;
}

.mt-pipeline {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}
.mt-step {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  background: #fff;
  border: 1px solid rgba(36, 25, 21, 0.1);
  border-radius: 8px;
  padding: 14px 18px;
}
.mt-step-num {
  flex: none;
  inline-size: 28px;
  block-size: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--wi-primary, #FF8551);
  color: #fff;
  font-size: 0.85rem;
}
.mt-step-body { margin: 0; line-height: 1.55; }

.mt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.mt-grid--3 { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }

.mt-card {
  background: #fff;
  border: 1px solid rgba(36, 25, 21, 0.1);
  border-radius: 8px;
  padding: 20px;
}
.mt-card--not { border-inline-start: 3px solid var(--wi-secondary, #006D44); }
.mt-card--wide { border-inline-start: 3px solid var(--wi-primary, #FF8551); }
.mt-card-title {
  font-family: var(--wi-font-title, 'Outfit', sans-serif);
  font-size: 1.05rem;
  margin: 0 0 8px;
}
.mt-card-body { margin: 0; line-height: 1.6; opacity: 0.88; }

.mt-cta { max-width: 780px; margin: 72px auto 0; text-align: center; }
.mt-cta-btn {
  display: inline-block;
  margin-block-start: 14px;
  padding: 12px 28px;
  border-radius: 8px;
  background: var(--wi-primary, #FF8551);
  color: #fff;
  text-decoration: none;
  font-family: var(--wi-font-title, 'Outfit', sans-serif);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.mt-cta-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(255, 133, 81, 0.35);
}
</style>
