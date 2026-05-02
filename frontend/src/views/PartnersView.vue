<!--
  US-062 — Page partenariats institutionnels Bassira (/partenaires)
  -----------------------------------------------------------------
  Cible : Heads of Research de think tanks (OCP Policy Center,
  Carnegie ME) et Partners de cabinets conseil (McKinsey,
  Roland Berger). Registre académique / institutionnel.

  Promesse : « Bassira complète vos méthodologies, ne les remplace pas. »

  Tokens : --wi-* exclusivement (Warm Intelligence). Zéro hex hardcodé.
  Typographies : Outfit (titres), Manrope (corps).
  i18n : FR / EN / AR avec gestion RTL via propriétés CSS logiques.
-->
<template>
  <div class="partners-page" :dir="$i18n.locale === 'ar' ? 'rtl' : 'ltr'">
    <!-- ───────── Top bar ───────── -->
    <header class="partners-topbar">
      <router-link
        to="/"
        class="partners-back"
        :title="$t('partners.nav.backTitle')"
      >
        <span
          class="partners-back-arrow material-symbols-outlined"
          aria-hidden="true"
        >arrow_back</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
    </header>

    <main class="partners-main">
      <!-- ───────── Hero institutionnel ───────── -->
      <section class="partners-hero">
        <span class="partners-pill">{{ $t('partners.hero.eyebrow') }}</span>
        <h1 class="partners-headline">{{ $t('partners.hero.title') }}</h1>
        <p class="partners-sub">{{ $t('partners.hero.subtitle') }}</p>
        <div class="partners-hero-cta">
          <a href="#contact" class="partners-cta-primary">
            {{ $t('partners.hero.cta') }}
            <span
              class="material-symbols-outlined"
              aria-hidden="true"
            >arrow_forward</span>
          </a>
        </div>
      </section>

      <!-- ───────── Logos partenaires ───────── -->
      <section class="partners-logos" aria-labelledby="partners-logos-title">
        <p id="partners-logos-title" class="partners-logos-title">
          {{ $t('partners.logos.title') }}
        </p>
        <div class="partners-logos-grid" aria-hidden="true">
          <div v-for="i in 8" :key="`logo-${i}`" class="partners-logo-placeholder"></div>
        </div>
        <p class="partners-logos-categories">
          {{ $t('partners.logos.categories') }}
        </p>
      </section>

      <!-- ───────── Comment ça marche (3 étapes) ───────── -->
      <section class="partners-process" aria-labelledby="partners-process-title">
        <h2 id="partners-process-title" class="partners-section-title">
          {{ $t('partners.process.title') }}
        </h2>
        <p class="partners-section-sub">{{ $t('partners.process.subtitle') }}</p>

        <ol class="partners-steps">
          <li class="partners-step">
            <div class="partners-step-num" aria-hidden="true">1</div>
            <h3 class="partners-step-title">{{ $t('partners.process.step1.title') }}</h3>
            <p class="partners-step-body">{{ $t('partners.process.step1.body') }}</p>
          </li>
          <span
            class="partners-step-arrow material-symbols-outlined"
            aria-hidden="true"
          >arrow_forward</span>
          <li class="partners-step">
            <div class="partners-step-num" aria-hidden="true">2</div>
            <h3 class="partners-step-title">{{ $t('partners.process.step2.title') }}</h3>
            <p class="partners-step-body">{{ $t('partners.process.step2.body') }}</p>
          </li>
          <span
            class="partners-step-arrow material-symbols-outlined"
            aria-hidden="true"
          >arrow_forward</span>
          <li class="partners-step">
            <div class="partners-step-num" aria-hidden="true">3</div>
            <h3 class="partners-step-title">{{ $t('partners.process.step3.title') }}</h3>
            <p class="partners-step-body">{{ $t('partners.process.step3.body') }}</p>
          </li>
        </ol>
      </section>

      <!-- ───────── Tiers de partenariat ───────── -->
      <section class="partners-tiers" aria-labelledby="partners-tiers-title">
        <h2 id="partners-tiers-title" class="partners-section-title">
          {{ $t('partners.tiers.title') }}
        </h2>
        <p class="partners-section-sub">{{ $t('partners.tiers.subtitle') }}</p>

        <div class="partners-tiers-grid">
          <!-- Research Partner -->
          <article class="partners-tier partners-tier--research">
            <span class="partners-tier-eyebrow">{{ $t('partners.tiers.research.eyebrow') }}</span>
            <h3 class="partners-tier-title">{{ $t('partners.tiers.research.title') }}</h3>
            <p class="partners-tier-body">{{ $t('partners.tiers.research.body') }}</p>
            <ul class="partners-tier-features">
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.research.feature1') }}
              </li>
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.research.feature2') }}
              </li>
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.research.feature3') }}
              </li>
            </ul>
            <a href="#contact" class="partners-tier-cta partners-tier-cta--ghost">
              {{ $t('partners.tiers.research.cta') }}
            </a>
          </article>

          <!-- Integration Partner (featured) -->
          <article class="partners-tier partners-tier--featured">
            <span class="partners-tier-badge">{{ $t('partners.tiers.featuredBadge') }}</span>
            <span class="partners-tier-eyebrow">{{ $t('partners.tiers.integration.eyebrow') }}</span>
            <h3 class="partners-tier-title">{{ $t('partners.tiers.integration.title') }}</h3>
            <p class="partners-tier-body">{{ $t('partners.tiers.integration.body') }}</p>
            <ul class="partners-tier-features">
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.integration.feature1') }}
              </li>
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.integration.feature2') }}
              </li>
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.integration.feature3') }}
              </li>
            </ul>
            <a href="#contact" class="partners-tier-cta partners-tier-cta--solid">
              {{ $t('partners.tiers.integration.cta') }}
            </a>
          </article>

          <!-- White-label -->
          <article class="partners-tier partners-tier--whitelabel">
            <span class="partners-tier-eyebrow">{{ $t('partners.tiers.whitelabel.eyebrow') }}</span>
            <h3 class="partners-tier-title">{{ $t('partners.tiers.whitelabel.title') }}</h3>
            <p class="partners-tier-body">{{ $t('partners.tiers.whitelabel.body') }}</p>
            <ul class="partners-tier-features">
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.whitelabel.feature1') }}
              </li>
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.whitelabel.feature2') }}
              </li>
              <li>
                <span class="material-symbols-outlined" aria-hidden="true">check</span>
                {{ $t('partners.tiers.whitelabel.feature3') }}
              </li>
            </ul>
            <a href="#contact" class="partners-tier-cta partners-tier-cta--terracotta">
              {{ $t('partners.tiers.whitelabel.cta') }}
            </a>
          </article>
        </div>
      </section>

      <!-- ───────── Témoignages ───────── -->
      <section
        class="partners-testimonials"
        aria-labelledby="partners-testimonials-title"
      >
        <h2 id="partners-testimonials-title" class="partners-section-title">
          {{ $t('partners.testimonials.title') }}
        </h2>

        <div class="partners-testimonials-grid">
          <figure class="partners-testimonial">
            <span
              class="partners-quote-icon material-symbols-outlined"
              aria-hidden="true"
            >format_quote</span>
            <blockquote class="partners-testimonial-text">
              {{ $t('partners.testimonials.quote1.text') }}
            </blockquote>
            <figcaption class="partners-testimonial-author">
              <span class="partners-testimonial-name">
                {{ $t('partners.testimonials.quote1.name') }}
              </span>
              <span class="partners-testimonial-role">
                {{ $t('partners.testimonials.quote1.role') }}
              </span>
              <span class="partners-testimonial-org">
                {{ $t('partners.testimonials.quote1.org') }}
              </span>
            </figcaption>
          </figure>

          <figure class="partners-testimonial">
            <span
              class="partners-quote-icon material-symbols-outlined"
              aria-hidden="true"
            >format_quote</span>
            <blockquote class="partners-testimonial-text">
              {{ $t('partners.testimonials.quote2.text') }}
            </blockquote>
            <figcaption class="partners-testimonial-author">
              <span class="partners-testimonial-name">
                {{ $t('partners.testimonials.quote2.name') }}
              </span>
              <span class="partners-testimonial-role">
                {{ $t('partners.testimonials.quote2.role') }}
              </span>
              <span class="partners-testimonial-org">
                {{ $t('partners.testimonials.quote2.org') }}
              </span>
            </figcaption>
          </figure>
        </div>
      </section>

      <!-- ───────── CTA contact ───────── -->
      <section
        id="contact"
        class="partners-contact"
        aria-labelledby="partners-contact-title"
      >
        <div class="partners-contact-inner">
          <h2 id="partners-contact-title" class="partners-contact-title">
            {{ $t('partners.contact.title') }}
          </h2>
          <p class="partners-contact-sub">{{ $t('partners.contact.subtitle') }}</p>

          <form class="partners-contact-form" @submit.prevent="onSubmit">
            <div class="partners-form-row">
              <label for="partners-name" class="partners-form-label">
                {{ $t('partners.contact.fields.name') }}
              </label>
              <input
                id="partners-name"
                v-model="form.name"
                type="text"
                class="partners-form-input"
                required
                :placeholder="$t('partners.contact.placeholders.name')"
              />
            </div>

            <div class="partners-form-row">
              <label for="partners-org" class="partners-form-label">
                {{ $t('partners.contact.fields.organization') }}
              </label>
              <input
                id="partners-org"
                v-model="form.organization"
                type="text"
                class="partners-form-input"
                required
                :placeholder="$t('partners.contact.placeholders.organization')"
              />
            </div>

            <div class="partners-form-row">
              <label for="partners-email" class="partners-form-label">
                {{ $t('partners.contact.fields.email') }}
              </label>
              <input
                id="partners-email"
                v-model="form.email"
                type="email"
                class="partners-form-input"
                required
                :placeholder="$t('partners.contact.placeholders.email')"
              />
            </div>

            <div class="partners-form-row">
              <label for="partners-message" class="partners-form-label">
                {{ $t('partners.contact.fields.message') }}
              </label>
              <textarea
                id="partners-message"
                v-model="form.message"
                rows="4"
                class="partners-form-textarea"
                :placeholder="$t('partners.contact.placeholders.message')"
              ></textarea>
            </div>

            <button type="submit" class="partners-form-submit">
              {{ $t('partners.contact.submit') }}
              <span
                class="material-symbols-outlined"
                aria-hidden="true"
              >send</span>
            </button>

            <p class="partners-form-note">
              {{ $t('partners.contact.fallbackNote') }}
              <a :href="`mailto:${PARTNER_EMAIL}`" class="partners-form-mailto">
                {{ PARTNER_EMAIL }}
              </a>
            </p>
          </form>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { reactive } from 'vue'

/**
 * Adresse de contact partenariats. Centralisée ici pour permettre une
 * future bascule vers une variable d'env (VITE_PARTNERS_EMAIL) si besoin.
 */
const PARTNER_EMAIL = 'partners@ai-mpower.com'

const form = reactive({
  name: '',
  organization: '',
  email: '',
  message: '',
})

/**
 * Soumission : aucun backend dédié n'existe pour cette route — on
 * compose un mailto: pré-rempli vers l'adresse partenariats. Cela
 * couvre le cas hors-ligne, évite la dépendance à un backend, et
 * laisse la trace de l'expéditeur dans son propre client.
 */
function onSubmit() {
  const subject = encodeURIComponent(
    `[Bassira Partners] ${form.organization || form.name || 'Demande'}`
  )
  const bodyLines = [
    `Nom : ${form.name}`,
    `Institution : ${form.organization}`,
    `Email : ${form.email}`,
    '',
    form.message || '',
  ]
  const body = encodeURIComponent(bodyLines.join('\n'))
  window.location.href = `mailto:${PARTNER_EMAIL}?subject=${subject}&body=${body}`
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   Page institutionnelle « partenariats »
   Tokens : --wi-* (Warm Intelligence) uniquement.
   Mises en page logiques (margin-inline, padding-inline) pour
   garantir un rendu correct en RTL (ar).
   ═══════════════════════════════════════════════════════════ */

.partners-page {
  min-height: 100vh;
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
}

/* ── Top bar ────────────────────────────────────────── */
.partners-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--wi-space-md) var(--wi-space-lg);
  border-bottom: 1px solid color-mix(in srgb, var(--wi-on-surface) 10%, transparent);
}

.partners-back {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  color: var(--wi-on-surface);
  text-decoration: none;
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-label-sm);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  transition: color 0.2s ease;
}
.partners-back:hover {
  color: var(--wi-primary);
}
.partners-back-arrow {
  font-size: 18px;
}
[dir="rtl"] .partners-back-arrow {
  transform: scaleX(-1);
}

/* ── Hero ──────────────────────────────────────────── */
.partners-main {
  max-width: 1280px;
  margin: 0 auto;
}

.partners-hero {
  text-align: center;
  padding: var(--wi-space-xl) var(--wi-space-lg) var(--wi-space-lg);
  max-width: 880px;
  margin: 0 auto;
}

.partners-pill {
  display: inline-flex;
  align-items: center;
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
  padding: 6px 14px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-body);
  font-weight: 600;
  font-size: var(--wi-label-sm);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: var(--wi-space-md);
}

.partners-headline {
  font-family: var(--wi-font-heading);
  font-size: clamp(32px, 5vw, var(--wi-h1-size));
  font-weight: var(--wi-h1-weight);
  line-height: var(--wi-h1-leading);
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-surface);
  margin: 0 0 var(--wi-space-md) 0;
}

.partners-sub {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-lg);
  line-height: var(--wi-body-lg-leading);
  font-weight: var(--wi-body-lg-weight);
  color: var(--wi-on-surface-variant);
  max-width: 640px;
  margin: 0 auto var(--wi-space-md);
}

.partners-hero-cta {
  margin-top: var(--wi-space-lg);
}

.partners-cta-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  background: var(--wi-on-surface);
  color: var(--wi-bg);
  padding: 14px 28px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-body-md);
  text-decoration: none;
  transition: background 0.2s ease, transform 0.1s ease;
}
.partners-cta-primary:hover {
  background: var(--wi-primary);
}
.partners-cta-primary:active {
  transform: scale(0.98);
}
[dir="rtl"] .partners-cta-primary .material-symbols-outlined {
  transform: scaleX(-1);
}

/* ── Logos partenaires ────────────────────────────── */
.partners-logos {
  border-block: 1px solid color-mix(in srgb, var(--wi-on-surface) 10%, transparent);
  background: var(--wi-surface);
  padding: var(--wi-space-lg) var(--wi-space-lg);
  text-align: center;
}

.partners-logos-title {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  margin: 0 0 var(--wi-space-md);
}

.partners-logos-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--wi-space-md);
  align-items: center;
  justify-items: center;
  max-width: 960px;
  margin: 0 auto var(--wi-space-md);
}

@media (min-width: 640px) {
  .partners-logos-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (min-width: 1024px) {
  .partners-logos-grid { grid-template-columns: repeat(8, minmax(0, 1fr)); }
}

.partners-logo-placeholder {
  width: 100%;
  max-width: 120px;
  height: 36px;
  background: var(--wi-surface-container-high);
  border-radius: var(--wi-radius-md);
  filter: grayscale(1);
  opacity: 0.7;
}

.partners-logos-categories {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  margin: 0;
  letter-spacing: 0.02em;
}

/* ── Section titles ───────────────────────────────── */
.partners-section-title {
  font-family: var(--wi-font-heading);
  font-size: clamp(24px, 4vw, var(--wi-h2-size));
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-surface);
  text-align: center;
  margin: 0 0 var(--wi-space-sm);
}

.partners-section-sub {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  text-align: center;
  max-width: 640px;
  margin: 0 auto var(--wi-space-lg);
}

/* ── Process (3 étapes) ───────────────────────────── */
.partners-process {
  padding: var(--wi-space-xl) var(--wi-space-lg);
}

.partners-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--wi-space-md);
  align-items: stretch;
}

@media (min-width: 768px) {
  .partners-steps {
    grid-template-columns: 1fr auto 1fr auto 1fr;
    align-items: center;
  }
}

.partners-step {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  text-align: center;
  box-shadow: var(--wi-shadow-sm);
}

.partners-step-num {
  width: 56px;
  height: 56px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
  font-family: var(--wi-font-heading);
  font-size: 24px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--wi-space-sm);
}

.partners-step-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  color: var(--wi-on-surface);
  margin: 0 0 var(--wi-space-xs);
}

.partners-step-body {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  margin: 0;
}

.partners-step-arrow {
  color: var(--wi-primary);
  font-size: 32px !important;
  display: none;
}

@media (min-width: 768px) {
  .partners-step-arrow { display: inline-flex; justify-self: center; }
}

[dir="rtl"] .partners-step-arrow {
  transform: scaleX(-1);
}

/* ── Tiers de partenariat ─────────────────────────── */
.partners-tiers {
  padding: var(--wi-space-xl) var(--wi-space-lg);
  background: var(--wi-surface-container-low);
  border-block: 1px solid var(--wi-outline-variant);
}

.partners-tiers-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--wi-space-md);
  max-width: 1080px;
  margin: 0 auto;
}

@media (min-width: 900px) {
  .partners-tiers-grid {
    grid-template-columns: repeat(3, 1fr);
    align-items: stretch;
  }
}

.partners-tier {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: var(--wi-shadow-sm);
}

.partners-tier--research {
  background: var(--wi-surface-container-low);
}

.partners-tier--featured {
  border: 2px solid var(--wi-primary-container);
  box-shadow: var(--wi-shadow-lg);
  background: var(--wi-surface);
}

@media (min-width: 900px) {
  .partners-tier--featured {
    transform: translateY(-12px);
  }
}

.partners-tier--whitelabel {
  border-top: 4px solid var(--wi-primary);
}

.partners-tier-badge {
  position: absolute;
  top: -14px;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  background: var(--wi-primary-container);
  color: var(--wi-on-primary);
  padding: 4px 12px;
  border-radius: var(--wi-radius-sm);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
[dir="rtl"] .partners-tier-badge {
  transform: translateX(50%);
}

.partners-tier-eyebrow {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  margin-bottom: var(--wi-space-xs);
}

.partners-tier-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: 600;
  line-height: var(--wi-h3-leading);
  color: var(--wi-on-surface);
  margin: 0 0 var(--wi-space-xs);
}

.partners-tier-body {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  margin: 0 0 var(--wi-space-md);
}

.partners-tier-features {
  list-style: none;
  margin: 0 0 var(--wi-space-md);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
  flex-grow: 1;
}

.partners-tier-features li {
  display: flex;
  align-items: flex-start;
  gap: var(--wi-space-xs);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface);
}

.partners-tier-features .material-symbols-outlined {
  color: var(--wi-secondary);
  font-size: 18px !important;
  margin-top: 2px;
  flex-shrink: 0;
}

.partners-tier-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px 20px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-body-md);
  text-decoration: none;
  transition: background 0.2s ease, color 0.2s ease, transform 0.1s ease;
  cursor: pointer;
  border: 1px solid transparent;
}
.partners-tier-cta:active {
  transform: scale(0.98);
}

.partners-tier-cta--ghost {
  background: transparent;
  color: var(--wi-on-surface);
  border-color: var(--wi-outline);
}
.partners-tier-cta--ghost:hover {
  background: var(--wi-surface-container);
}

.partners-tier-cta--solid {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary);
}
.partners-tier-cta--solid:hover {
  background: var(--wi-primary);
}

.partners-tier-cta--terracotta {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
}
.partners-tier-cta--terracotta:hover {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary);
}

/* ── Témoignages ──────────────────────────────────── */
.partners-testimonials {
  padding: var(--wi-space-xl) var(--wi-space-lg);
}

.partners-testimonials-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--wi-space-md);
  max-width: 1080px;
  margin: 0 auto;
}

@media (min-width: 768px) {
  .partners-testimonials-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.partners-testimonial {
  position: relative;
  background: var(--wi-surface-container-high);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-lg) var(--wi-space-md) var(--wi-space-md);
  margin: 0;
  overflow: hidden;
}

.partners-quote-icon {
  position: absolute;
  top: var(--wi-space-sm);
  inset-inline-start: var(--wi-space-sm);
  font-size: 56px !important;
  color: color-mix(in srgb, var(--wi-primary) 15%, transparent);
  pointer-events: none;
}

.partners-testimonial-text {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-body-lg);
  line-height: 1.5;
  color: var(--wi-on-surface);
  margin: 0 0 var(--wi-space-md);
  position: relative;
  z-index: 1;
}

.partners-testimonial-author {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.partners-testimonial-name {
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface);
}

.partners-testimonial-role {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}

.partners-testimonial-org {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--wi-secondary);
}

/* ── CTA contact ──────────────────────────────────── */
.partners-contact {
  background: var(--wi-on-surface);
  color: var(--wi-bg);
  padding: var(--wi-space-xl) var(--wi-space-lg);
}

.partners-contact-inner {
  max-width: 720px;
  margin: 0 auto;
}

.partners-contact-title {
  font-family: var(--wi-font-heading);
  font-size: clamp(24px, 4vw, var(--wi-h2-size));
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-bg);
  text-align: center;
  margin: 0 0 var(--wi-space-sm);
}

.partners-contact-sub {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: color-mix(in srgb, var(--wi-bg) 75%, transparent);
  text-align: center;
  margin: 0 auto var(--wi-space-lg);
  max-width: 560px;
}

.partners-contact-form {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}

.partners-form-row {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
}

.partners-form-label {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--wi-bg) 75%, transparent);
}

.partners-form-input,
.partners-form-textarea {
  width: 100%;
  background: color-mix(in srgb, var(--wi-bg) 8%, transparent);
  color: var(--wi-bg);
  border: 1px solid color-mix(in srgb, var(--wi-bg) 20%, transparent);
  border-radius: var(--wi-radius-interactive);
  padding: 12px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  transition: border-color 0.2s ease, background 0.2s ease;
}

.partners-form-input::placeholder,
.partners-form-textarea::placeholder {
  color: color-mix(in srgb, var(--wi-bg) 45%, transparent);
}

.partners-form-input:focus,
.partners-form-textarea:focus {
  outline: none;
  border-color: var(--wi-primary-container);
  background: color-mix(in srgb, var(--wi-bg) 12%, transparent);
}

.partners-form-textarea {
  resize: vertical;
  min-height: 120px;
}

.partners-form-submit {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: none;
  padding: 14px 28px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-body-md);
  cursor: pointer;
  transition: background 0.2s ease, transform 0.1s ease;
}
.partners-form-submit:hover {
  background: var(--wi-primary-container);
}
.partners-form-submit:active {
  transform: scale(0.98);
}
[dir="rtl"] .partners-form-submit .material-symbols-outlined {
  transform: scaleX(-1);
}

.partners-form-note {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: color-mix(in srgb, var(--wi-bg) 65%, transparent);
  text-align: center;
  margin: 0;
}

.partners-form-mailto {
  color: var(--wi-inverse-primary);
  text-decoration: underline;
}
.partners-form-mailto:hover {
  color: var(--wi-bg);
}

/* ── Reduced motion ──────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .partners-cta-primary,
  .partners-form-submit,
  .partners-tier-cta,
  .partners-back {
    transition: none;
  }
  .partners-tier--featured {
    transform: none !important;
  }
}
</style>
