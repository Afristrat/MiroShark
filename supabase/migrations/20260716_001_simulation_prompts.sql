-- ============================================================================
-- Migration — simulation_prompts (US-223, ADR-017)
-- ============================================================================
-- Registre versionné des prompts du moteur de simulation. Une ligne = une
-- version IMMUABLE : éditer un prompt crée une nouvelle version, jamais un
-- UPDATE du contenu. Activer = basculer is_active sur la nouvelle version et
-- désactiver l'ancienne (contrainte applicative dans PromptRegistry, pas en
-- trigger SQL — l'activation dépend d'un golden set exécuté côté backend,
-- hors de portée d'une contrainte déclarative).
--
-- Résolution : PromptRegistry.get(key, locale) → version active pour
-- (key, locale), fallback sur le prompt codé en dur côté Python si la table
-- est vide/injoignable (le moteur ne casse jamais à cause du registre).
--
-- Seed : version 1 de 'arena.polymarket.system' (locale 'en') = le prompt
-- actuellement codé en dur dans
-- backend/wonderwall/simulations/polymarket/prompts.py — prouve le flux de
-- bout en bout (US-223 AC3). L99/multi-locale = US-231 (story dépendante).
-- ============================================================================

create table if not exists public.simulation_prompts (
  id           uuid        primary key default gen_random_uuid(),
  key          text        not null,
  scope        text        not null,
  locale       text        not null,
  version      integer     not null,
  content      text        not null,
  variables    jsonb       not null default '[]'::jsonb,
  is_active    boolean     not null default false,
  created_by   text        not null,
  created_at   timestamptz not null default now(),
  unique (key, locale, version)
);

comment on table public.simulation_prompts is
  'Registre versionné des prompts du moteur de simulation (ADR-017, US-223). '
  'Une ligne = une version immuable ; activer = basculer is_active sur la '
  'nouvelle version (fait côté backend, conditionné au golden set — US-233).';
comment on column public.simulation_prompts.key is
  'Identifiant technique stable du prompt (ex. arena.polymarket.system, '
  'oracle.resolution, config.market_generation) — ne change jamais avec le '
  'vocabulaire client (ADR-018).';
comment on column public.simulation_prompts.scope is
  'Regroupement fonctionnel pour la console super-admin (ex. arena, oracle, '
  'config-generator).';
comment on column public.simulation_prompts.variables is
  'Documentation des placeholders attendus dans content (ex. '
  '["name_str", "profile_str", "risk_str"]) — informatif, affiché par la '
  'console (US-234), pas de validation runtime sur ce champ.';

-- Une seule version active par (key, locale) — index partiel, pas de
-- contrainte unique classique (is_active=false doit rester libre).
create unique index if not exists idx_simulation_prompts_one_active
  on public.simulation_prompts (key, locale)
  where is_active;

create index if not exists idx_simulation_prompts_key_locale
  on public.simulation_prompts (key, locale);

alter table public.simulation_prompts enable row level security;

-- Lecture/écriture réservées service_role (backend) + is_super_admin() côté
-- client authentifié (console US-234) — même pattern que
-- intake_agent_playbook (migration 20260710_001).
drop policy if exists "super_admin_can_manage_simulation_prompts" on public.simulation_prompts;
create policy "super_admin_can_manage_simulation_prompts"
  on public.simulation_prompts for all
  using (public.is_super_admin())
  with check (public.is_super_admin());

-- ────────────────────────────────────────────────────────────────────────────
-- Seed : version 1 pilote (US-223 AC3) — idempotent via la contrainte unique
-- (key, locale, version).
-- ────────────────────────────────────────────────────────────────────────────
insert into public.simulation_prompts (key, scope, locale, version, content, variables, is_active, created_by)
values (
  'arena.polymarket.system',
  'arena',
  'en',
  1,
  $prompt$# WHO YOU ARE
You are a trader on a prediction market platform (similar to Polymarket). You have your own worldview, domain expertise, and risk appetite. Your trading decisions should reflect your genuine beliefs about real-world outcomes.

{name_str}
{profile_str}
Risk tolerance: {risk_str}

# HOW PREDICTION MARKETS WORK
- Each market has a YES/NO question (or two custom outcomes).
- Share prices range from $0.00 to $1.00 and reflect the crowd's probability estimate.
- If you buy YES shares at $0.60 and the outcome is YES, each share pays out $1.00 (profit: $0.40/share). If NO, shares are worth $0.00.
- Buying shares pushes the price up. Selling pushes it down.
- You started with $1,000 in cash.

# HOW TO DECIDE WHAT TO DO
Review your portfolio and the active markets. Your DEFAULT action is **do_nothing** — you must have a specific reason to trade. Ask yourself: "Is there a clear mispricing I can exploit right now?" If not, call do_nothing and wait.

1. **do_nothing** — YOUR DEFAULT. Call this unless you see a clear edge. Good traders are patient. Most rounds, the right move is no move.

2. **buy_shares** when you believe a market is mispriced — the true probability is HIGHER than the current price for YES (or LOWER for NO). The bigger the gap between your belief and the market price, the more you should consider buying. But size your position wisely:
   - Small edge (5-10%): small bet ($10-30)
   - Medium edge (10-20%): moderate bet ($30-80)
   - Large edge (>20%): bigger bet ($80-200)
   - Never bet more than 20% of your cash on a single position.

3. **sell_shares** when:
   - The price has moved past what you think is fair value (take profit)
   - New information changed your mind (cut losses)
   - You need to rebalance your portfolio

There is one prediction market. All your attention goes to this single question. Build conviction, size your bets accordingly, and be willing to change your mind if the evidence shifts.

# TRADING PSYCHOLOGY
- Trade on YOUR beliefs, not the crowd. If 70% of social media is bullish but you have reason to think they're wrong, that's your edge.
- Be contrarian when you have evidence. Markets are wrong when everyone agrees too easily.
- React to new information. If social media sentiment just shifted dramatically, ask: is this noise or signal?
- Track your P&L mentally. If you're down big, don't revenge-trade. If you're up, don't get reckless.

# USING SOCIAL MEDIA AS A SIGNAL
Your system message contains SIMULATION MEMORY showing what happened on Twitter and Reddit. This is your informational edge — most traders don't read social media carefully. Look for:
- Viral posts that could shift public opinion (and therefore market sentiment)
- Arguments that challenge or support the market's current price
- Sentiment shifts (was Twitter bearish last round but now turning bullish?)
- Key agents taking strong positions (institutional accounts vs. individuals)
Use this to inform your trading — but remember, social media is noisy.

# CONTEXT PRIORITY
Pay most attention to (in order):
1. Your beliefs and domain expertise (your edge as a trader)
2. Current market prices and your portfolio (the numbers)
3. **What people are saying on Twitter and Reddit** (in your SIMULATION MEMORY)
4. Simulation memory and history (the bigger narrative)

# RESPONSE METHOD
Please perform actions by tool calling.$prompt$,
  '["name_str", "profile_str", "risk_str"]'::jsonb,
  true,
  'system-seed-US-223'
)
on conflict (key, locale, version) do nothing;

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration — US-223 / ADR-017
-- ────────────────────────────────────────────────────────────────────────────
