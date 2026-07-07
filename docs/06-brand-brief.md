# Brand Brief — Bassira (بصيرة)

> Consolidé le 2026-07-07 depuis les références LUES du repo : design system Stitch
> exporté (`stitch_bassira_global_design_system/bassira_causse/DESIGN.md` — direction
> « Bauhaus / Artisanal Luxury / terracotta »), `bassira_brand_prompts.md:14-36`, défauts
> SQL de `pdf_branding` (migration 20260506_001), séquences Apollo et calendrier LinkedIn.
> Bassira = « clairvoyance » en arabe. La marque visible est Bassira ; `miroshark` reste
> un identifiant technique interne, jamais montré à l'utilisateur.

## Ressenti cible

**Clairvoyant · Artisanal · Institutionnel.**
La contradiction tranchée : le produit simule des réseaux sociaux (univers « fun/viral »)
mais se vend à des COMEX — le ressenti retenu est celui du cabinet de prospective
haut de gamme (chaleur terracotta, luxe artisanal), PAS celui du jouet tech. Tout écran
qui « fait gadget » trahit la marque.

## Palette (« Causse » / Warm Intelligence — tokens `--wi-*`)

| Usage | Hex | Note |
|---|---|---|
| Primaire (accent, CTA) | `#FF8551` | Orange terracotta chaud |
| Secondaire (validation, contrepoint) | `#006D44` | Vert profond |
| Fond | `#FAF7F2` | Crème |
| Texte | `#241915` | Brun quasi-noir |

Ces 4 valeurs sont AUSSI les défauts SQL de `pdf_branding` — toute évolution de palette
se répercute dans la migration ET ici, même commit. Le legacy `--ms-*` (« Playful & Soft »)
est en extinction : ne plus en introduire (règle CLAUDE.md).

## Typographie

- **Titres** : Outfit
- **Corps** : Manrope
- **Arabe** : Tajawal (bascule automatique `[lang="ar"]`, design-tokens.css:281-289)
- **Monospace** (IDs, chiffres techniques) : JetBrains Mono

## Voix du copy

Registre : **vouvoiement, direct, institutionnel avec chaleur** — le ton d'un associé
senior qui parle à un dirigeant, jamais celui d'une app grand public. Chiffres concrets
et enjeux nommés (référence de ton, séquences Apollo : « Sur un comité d'investissement
à 200 M€, ça déplace le seuil de décision sans changer votre univers de risque »).
Interdits : « prédiction », « magique », promesses de certitude, superlatifs non sourcés.

**3 exemples rédigés dans la voix :**

- **Message d'erreur** : « La génération de la configuration a échoué — le graphe de ce
  scénario est vide. Reprenez à l'étape 1 pour reconstruire l'extraction ; vos documents
  sont conservés. »
- **Empty state** (dashboard sans simulation) : « Aucune simulation pour l'instant.
  Déposez un communiqué, un projet de décision ou une question stratégique — la première
  cartographie de réactions prend une dizaine de minutes. »
- **E-mail de bienvenue** — Objet : « Votre espace Bassira est ouvert » — Première ligne :
  « Bonjour {{prénom}}, votre organisation dispose désormais d'un espace de stress-test
  décisionnel. Votre première simulation se lance en trois étapes ; comptez dix minutes. »

## Langues et directionnalité

**FR (pivot) + EN + AR avec RTL complet dès la v1** — déjà implémenté (parité vérifiée :
2013 clés × 3 locales, bascule `dir`/Tajawal automatique). Décision consignée ADR-008.
Règle de vie : toute clé ajoutée l'est dans les 3 locales du même commit ; le disclaimer
PDF est trilingue par défaut (fr/en/ar, cf. `pdf_branding.disclaimer_text`).

## Dettes de marque connues (backlog US-210)

1. Watermark d'export de graphiques = logo requin MiroShark (`chartExport.js:10`) — le
   seul artefact de marque qui SORT de l'app ; à remplacer en priorité absolue.
2. `public/miroshark-nobg.png` : le PNG doit être régénéré au branding Bassira (TODO
   documenté depuis 2026-04-29, `.ralph/progress.md:34`).
3. Section MCP de SettingsPanel + lien GitHub d'ExploreView encore MiroShark.
4. Vitrine (Causse) vs cœur produit (Playful & Soft) : expérience visuelle non unifiée —
   parking lot avec condition de sortie (04-feature-backlog).
5. **Domaine : bassira.ma TOUJOURS** (directive Amine 2026-07-07, ADR-013) — le défaut
   SQL du footer PDF (« bassira.ai ») et tout lien résiduel divergent sont à corriger ;
   emails Resend expédiés depuis l'adresse AI-MPower, liens pointant bassira.ma.
