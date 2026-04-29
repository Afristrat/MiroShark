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
