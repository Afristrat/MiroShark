# MiroShark — Design system « Playful & Soft »

Direction visuelle douce et chaleureuse. Vanilla CSS, sans framework. Tokens centralisés dans `src/design-tokens.css`, utilitaires dans `src/styles/components.css`.

## Palette

| Rôle | Variable | Valeur |
|---|---|---|
| Primaire (orange chaleureux) | `--ms-orange` | `#FF8551` |
| Primaire pressé | `--ms-orange-strong` | `#F26B36` |
| Secondaire (bleu pastel) | `--ms-blue` | `#5A7FDB` |
| Succès (vert menthe) | `--ms-mint` | `#7FD8A6` |
| Warning (pêche) | `--ms-peach` | `#FFB347` |
| Danger (rose doux) | `--ms-rose` | `#F4847A` |
| Fond crème | `--ms-bg` | `#FAF7F2` |
| Surface élevée | `--ms-bg-elevated` | `#FFFFFF` |
| Texte primaire | `--ms-text` | `#2A2A35` |
| Texte secondaire | `--ms-text-muted` | `#6B6B7D` |

Chaque couleur a une variante « soft » à faible opacité (`--ms-orange-soft`, etc.) pour les badges et états hover.

## Typographie

- **Titres** : `--ms-font-display` → Outfit (Google Fonts)
- **Corps** : `--ms-font-body` → Manrope
- **Mono / metrics** : `--ms-font-mono` → JetBrains Mono

Tailles : `--ms-text-xs` (12px) → `--ms-text-4xl` (48px).

## Spacing — échelle 4 / 8 / 12 / 16 / 20 / 24 / 32 / 48

Variables `--ms-space-1` (4px) à `--ms-space-12` (48px). Toujours utiliser ces tokens, jamais de valeurs en dur.

## Radius / shadow

- `--ms-radius-sm` (8px) — boutons, inputs
- `--ms-radius-md` (12px) — cartes
- `--ms-radius-lg` (24px) — grands containers, modales
- `--ms-radius-pill` — badges et avatars ronds
- Ombres : `--ms-shadow-xs` à `--ms-shadow-lg`. La carte par défaut utilise `--ms-shadow-md`.

## Classes utilitaires `.ms-*`

```html
<div class="ms-card ms-card--interactive">
  <h3 class="ms-card__title">Titre</h3>
  <p class="ms-card__subtitle">Description courte</p>
  <div class="ms-row">
    <button class="ms-btn ms-btn-primary">Lancer</button>
    <button class="ms-btn ms-btn-ghost">Annuler</button>
    <span class="ms-badge ms-badge-success">Prêt</span>
  </div>
</div>

<input class="ms-input" placeholder="URL…" />
<div class="ms-skeleton" style="height: 80px"></div>
```

Boutons : `.ms-btn-primary` (orange), `.ms-btn-secondary` (bleu), `.ms-btn-ghost` (transparent), `.ms-btn-danger`. Modificateurs : `.ms-btn--sm`, `.ms-btn--lg`, `.ms-btn--full`.

Badges : `.ms-badge-success | -warning | -info | -danger | -neutral`.

Helpers : `.ms-stack` (gap vertical 16px), `.ms-row` (flex), `.ms-text-muted`, `.ms-mono`, `.ms-anim-fade-in`.

## Animations

- Fade-in 300 ms à l'apparition (`@keyframes ms-fade-in`)
- Lift au survol (`translateY(-2px)` + ombre montée) sur cartes interactives
- `scale(1.02)` au hover sur boutons primaires
- Tout est désactivé sous `prefers-reduced-motion: reduce`

## Palette « legacy » (newspaper/terminal)

Pour zéro régression visuelle sur les composants antérieurs au rebrand Bassira (Home, Step1‑5, SettingsPanel, HistoryDatabase, DebugPanel, GraphPanel…), une seconde palette est définie dans `design-tokens.css`. Elle conserve les hex des anciens écrans tout en les centralisant.

| Rôle | Long | Alias court |
|---|---|---|
| Orange punchy | `--ms-legacy-orange` | `--lo` (`#FF6B1A`) |
| Surface paper | `--ms-legacy-paper` | `--lp` (`#FAFAFA`) |
| Encre noire | `--ms-legacy-ink` | `--li` (`#0A0A0A`) |
| Vert "available" | `--ms-legacy-success` | `--ls` (`#43C165`) |
| Rouge "error" | `--ms-legacy-danger` | `--ld` (`#FF4444`) |
| Surface secondaire | `--ms-legacy-paper-alt` | `--lp2` (`#F5F5F5`) |
| Encre dégradée | `--ms-legacy-ink-soft` | `--li2` (`#1A1A1A`) |

Variantes complémentaires : `--ms-legacy-orange-soft|strong|dark`, `--ms-legacy-success-dark`, `--ms-legacy-danger-dark`, `--ms-legacy-warning`, `--ms-legacy-muted` à `--ms-legacy-muted-6` (gris terminal).

Les **alias courts** (`--lo`, `--lp`…) sont utilisés dans le CSS final pour optimiser la taille du bundle ; les noms longs restent l'API publique recommandée pour la lisibilité.

> Direction long terme : fondre progressivement la palette legacy vers `--ms-orange` / `--ms-rose` à chaque refonte d'écran. Les nouveaux écrans Bassira (Calibration, ReviewEntities, Comparison) doivent utiliser exclusivement les tokens `--ms-*`.

## Palette catégorielle « charts »

`--ms-chart-1` à `--ms-chart-10` : ordre d'attribution recommandé pour D3 et autres dataviz. Les hex correspondants sont également disponibles inline dans les tableaux JS de `GraphPanel`, `NetworkPanel`, `PolymarketChart` (cas raisonné — palette runtime).

## Palette « status » Tailwind

Pour les états de qualité, accuracy et démographie utilisés dans `HistoryDatabase`, `EmbedDialog`, `DemographicBreakdown`, `BeliefDriftChart` :

| Rôle | Variable |
|---|---|
| Succès | `--ms-status-success` (`#22c55e`) |
| Warning | `--ms-status-warning` (`#f59e0b`) |
| Danger | `--ms-status-danger` (`#ef4444`) |
| Info | `--ms-status-info` (`#3b82f6`) |
| Pink (démographie) | `--ms-status-pink` (`#ec4899`) |
| Violet | `--ms-status-violet` (`#7C3AED`) |

Variantes `-strong`, `-text`, `-soft` disponibles selon le rôle (cf. `design-tokens.css`).

## Z-index — échelle unique

Pour éviter les collisions (modales sous panneaux flottants, etc.), `design-tokens.css` définit :

| Couche | Variable | Valeur |
|---|---|---|
| Dropdowns | `--ms-z-dropdown` | 900 |
| Sticky | `--ms-z-sticky` | 950 |
| Modal backdrop | `--ms-z-modal-backdrop` | 1000 |
| Modal | `--ms-z-modal` | 1050 |
| Popover | `--ms-z-popover` | 1200 |
| Toast | `--ms-z-toast` | 1400 |
| Floating LanguageSwitcher | `--ms-z-floating-lang` | 1500 |

## Composants factorisés (US-016)

Auparavant dupliqués dans 3+ fichiers, désormais dans `styles/components.css` :

```html
<!-- Stat card -->
<div class="stat-card">
  <span class="stat-value">42</span>
  <span class="stat-label">Agents</span>
</div>

<!-- Spinners (couleur héritée via currentColor) -->
<span class="ms-spinner ms-spinner--sm"></span>
<span class="ms-spinner ms-spinner--orange"></span>
<span class="loading-spinner-small"></span>      <!-- alias compat -->
<span class="spinner-sm"></span>                  <!-- alias compat -->
<div class="loading-spinner"></div>               <!-- alias compat -->

<!-- Empty state -->
<div class="ms-empty-state">
  <span class="ms-empty-state__icon">📭</span>
  <p class="ms-empty-state__title">Aucune donnée</p>
  <p class="ms-empty-state__hint">Ajoutez une simulation pour commencer.</p>
</div>

<!-- Toast -->
<div class="ms-toast ms-toast--success">Sauvegardé</div>

<!-- Badge legacy (base + variants locaux) -->
<span class="badge success">PRÊT</span>
<span class="badge processing"><span class="badge-dot"></span> EN COURS</span>
```

`@keyframes spin`, `@keyframes pulse` (`50% { opacity: 0.5 }`), `@keyframes fadeIn` sont également déclarés une seule fois dans `components.css`. Les composants peuvent les réutiliser via `animation: spin 0.8s linear infinite;` sans redéclaration locale.

## Règles d'or (US-016)

1. **Aucune valeur hex en dur** dans un nouveau fichier `.vue` ou `.css`. Toujours utiliser `var(--ms-*)`. Exceptions documentées : palettes chart D3 dans des strings JS, palettes Stitch isolées (`OffersView.vue`, `QuoteView.vue`), `design-tokens.css` (source de vérité).
2. **Aucun `!important`** sauf justification explicite par commentaire (override de style scoped Vue, conflit PWA inline). Préférer monter la spécificité avec un sélecteur composé (ex: `.parent .child.child`).
3. **Pas de redéclaration** de `@keyframes spin`, `@keyframes pulse`, `.stat-card`, `.badge` base — réutiliser ceux de `components.css`.
