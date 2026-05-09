# Pipeline de recherche dynamique seed → strategy → topics → briefs

> **Statut** : Draft v2 (post-feedback "étriqué"). Phase 0 du chantier Kairos↔Bassira.
> **Dernière MAJ** : 2026-05-09
> **BYOK** : aucun modèle ni provider imposé. Tasks Kairos résolues runtime via `settings.model_config[task]`.

## Pourquoi ce pipeline existe

Bassira est positionnée prospective stratégique MENA+Europe multi-secteurs. Une "graine de réalité" (prompt user libre, sujet quelconque, doc, URL) doit produire des briefs simulables RICHES — pas une simple liste de questions cadrées. Cela suppose :

- **Recherche multi-source réelle** (X, Reddit, ArXiv, RSS, web) avec sources adaptées à la graine, pas un tableau figé.
- **Multi-langue native** : un sujet Maroc peut avoir des signaux pertinents en FR, AR, EN. Le pipeline ne pénalise jamais un signal pour sa langue.
- **Détection de tensions et contradictions** : un topic qui ne contient que des signaux convergents est un cul-de-sac analytique. Les contradictions sont la matière première de la prospective.
- **Anti-blind-spot MENA-Europe** : la presse francophone domine les signaux MA/DZ/TN. Sans correction explicite, tout converge vers Le Monde et oublie les sources arabes, anglophones, locales.
- **Iterative deepening** : si le 1ᵉʳ pass révèle un gap (subject sans signal, contradiction non explorée, signal faible isolé), un 2ᵉ pass scopé sur le gap est lancé automatiquement.
- **Briefs multi-versions** : chaque topic propose 1-3 angles de framing différents (policy / market / crisis...) pour que l'utilisateur Bassira choisisse celui qui matche son besoin.

Aucune rubric figée par secteur. Aucune persistance polluante. Récursivité bornée (max depth 2).

## Architecture pipeline

```
[Bassira /console]  user pose graine (libre)
      │
      ▼
[Bassira backend]   POST /api/research/from-seed { seed, lang, sector_hint?, depth_hint? }
                    cache LRU 1h sur sha256(seed+lang+depth_hint)
      ▼
[Kairos]            POST /functions/v1/research-from-seed
                    header X-Bassira-API-Key
      │
      ├──► (★) PROMPT 1 — research-strategist (task=enrichment)
      │     output: research_strategy = subjects[] + tensions[] + blind_spots[]
      │            + language_mix + recursion_budget
      │
      ├──► (★) PROMPT 2 — rubric-architect (task=enrichment)
      │     output: rubric { criteria[], disqualifiers[], soft_boosts[] }
      │
      ▼
[scrape parallèle multi-langue]  X / Reddit / ArXiv / RSS / web
      → signals_session (table éphémère TTL 1h)
      │
      ▼
[score]  llm-score-batch (task=scoring, rubric_override en body)
         → top N signaux retenus + signaux disqualifiés tagués
      │
      ▼
PROMPT 3 — signal-synthesizer (task=enrichment)
  output: topics[] avec :
    - brief_variants (1-3 angles différents)
    - tensions internes (signaux contradictoires)
    - provenance (key_signals, supporting/conflicting)
    - confidence
  + coverage_map (subjects sans signal)
  + devil_advocate_topic (forcé)
      │
      ▼
PROMPT 4 — quality-auditor (task=enrichment)
      │
      ├── verdict=pass → return
      ├── verdict=warn → return + flag, log
      └── verdict=fail|gap_detected
             │
             ▼
        PROMPT 5 — iterative-deepening (task=enrichment)
             │  reformule un sub_seed scopé sur le gap
             ▼
        Re-pipeline (depth+1, max depth=2)
             │
             ▼
        Final merge avec output initial

★ étapes 1+2 lancées en parallèle dès la réception du seed.
```

## Conventions communes aux 5 prompts

- **Langue** : paramètre `lang ∈ {fr, en, ar}` injecté via `{{lang}}` pour la sortie. **Les signaux peuvent être multilingues** ; les prompts gèrent.
- **FR DEFCON 1** : accents obligatoires partout (É, È, À, Ç, Ê, Ô, Î, Ù, Û).
- **AR-friendly** : si lang=ar, RTL respect, pas de mélange LTR sauf acronymes/URLs.
- **Sanitisation** : INTERDIT `<tool_call>`, `<thinking>`, `<scratchpad>`, balises XML, markdown, préambule, justification hors-JSON. Sanitisation appliquée côté Kairos via `sanitize_llm_output` AVANT retour Bassira.
- **Output** : JSON strict uniquement, parsable sans heuristique.
- **No invention** : jamais de handle X, sub Reddit, signal_id ou source non fourni en input. Tout hint est qualifié `confident: true|false`.
- **Hedge calibré** : chaque output structuré (brief, rubric, topic) porte un `confidence ∈ [0,1]`. Pas de fake confidence à 0.9 par défaut.
- **BYOK** : tasks Kairos résolues runtime. Tier suggéré informatif, le user décide via `settings.model_config[task]`.

---

## PROMPT 1 — `research-strategist`

**Task Kairos** : `enrichment`
**Tier suggéré** : raisonnement (planification multi-axes).
**Rôle** : transforme une graine en **stratégie de recherche complète**, pas juste une liste de sujets.

### Système

```
Tu es un architecte de stratégie de recherche prospective. Ton rôle n'est
pas de résumer la graine, mais de la DÉCOMPOSER en axes de recherche
orthogonaux qui maximisent la diversité des signaux récupérés en aval.

MÉTHODOLOGIE OBLIGATOIRE :
1. Lis la graine. Identifie le DOMAINE (politique/finance/santé/cyber/marché/
   géopolitique/social/scientifique/produit/...) et le PÉRIMÈTRE GÉOGRAPHIQUE
   (Maroc / MENA / Afrique / Europe / monde). Ces deux dimensions cadrent
   le mix linguistique attendu.

2. Liste les ANGLES pertinents parmi les 8 disponibles :
   - actors          : qui décide, qui résiste, qui arbitre
   - metrics         : indicateurs chiffrés invoqués par les acteurs
   - precedents      : événements analogues passés (3 dernières années max)
   - counter         : positions opposées à la lecture dominante
   - weak-signals    : signaux faibles, niches, secteurs informels
   - context         : structure de fond (réglementaire, démographique...)
   - velocity        : signes que la situation accélère ou ralentit
   - second-order    : conséquences indirectes peu discutées
   Choisis 4-7 angles. Aucun doublon. Si la graine est étroite, force-toi
   à inclure counter + weak-signals (anti-echo-chamber).

3. Pour CHAQUE angle, formule UN sujet de recherche concret. Ne pas
   redonder, ne pas paraphraser la graine.

4. ÉVALUATION DE LA COMPLEXITÉ : si la graine est large/floue, demande
   plus de subjects (jusqu'à 12). Si la graine est précise/étroite, 3
   subjects suffisent. Adaptatif, pas un quota fixe.

5. Pour chaque sujet, propose des SOURCES diversifiées en LANGUE :
   - sub_queries en {{lang}} ET dans la langue dominante du périmètre
     géographique (FR pour Maroc, AR si la graine touche l'opinion
     publique arabe, EN pour signaux internationaux ou techniques).
   - Les hints (X handles, subs, ArXiv) doivent être DIVERSIFIÉS en
     langue. Un sujet Maroc avec UNIQUEMENT des handles francophones
     est un anti-pattern.

6. IDENTIFIE les TENSIONS connues entre subjects. Une tension = deux
   sujets dont les signaux vont probablement se contredire. C'est un
   atout, pas un défaut. Liste explicite (peut être vide).

7. IDENTIFIE les BLIND-SPOTS prévisibles. Quels angles risquent d'être
   sous-couverts par les sources mainstream ? À utiliser en aval pour
   forcer le scrape vers ces zones.

8. RECOMMANDE un budget de récursion : depth_max ∈ {0, 1, 2}. Une graine
   simple → 0. Une graine complexe avec tensions explicites → 2.

INTERDICTIONS :
- Pas de hint inventé (handle X qui n'existe pas, sub Reddit fictif).
- Pas de subject vague ("contexte général", "actualité du sujet").
- Pas de sub_queries génériques ("X 2026"). Toujours acteur+verbe+contexte.
- Pas de couverture homogène : si tous les subjects pointent les mêmes
  sources, échec de mission.

SCHEMA OUTPUT :
{
  "domain": "string (politique|finance|santé|...|autre)",
  "geo_scope": "string (MA|DZ|TN|MENA|MENA+EU|EU|world|other)",
  "language_mix": ["fr", "ar", "en"],
  "subjects": [
    {
      "id": "s_001",
      "title": "string 5-15 mots",
      "angle": "actors|metrics|precedents|counter|weak-signals|context|velocity|second-order",
      "rationale": "20-40 mots, justification de l'angle pour CETTE graine",
      "sub_queries": [
        { "q": "string requête", "lang": "fr|en|ar" },
        ...
      ],
      "rss_keywords": ["lower-case", "bigrammes acceptés"],
      "x_handles_hint": [
        { "handle": "@xxx", "lang": "fr|en|ar", "confident": true|false }
      ] | null,
      "reddit_subs_hint": [
        { "sub": "name", "confident": true|false }
      ] | null,
      "arxiv_categories_hint": ["cs.AI"] | null,
      "expected_signal_volume": "low|medium|high",
      "confidence": 0.0-1.0
    }
  ],
  "tensions": [
    {
      "between": ["s_001", "s_002"],
      "nature": "string 10-20 mots",
      "exploit_in_synthesis": true|false
    }
  ],
  "blind_spots": [
    {
      "description": "string 10-20 mots",
      "mitigation_query": "string requête de compensation"
    }
  ],
  "recursion_budget": 0|1|2
}
```

### Few-shot 1 — politique MA (FR)

**Input :**
```json
{
  "seed": "Réforme du Code du travail au Maroc en 2026 : flexibilité du contrat à durée déterminée, droit de grève, conventions collectives. Tension CGEM/syndicats CDT-UMT.",
  "lang": "fr",
  "sector_hint": "politics"
}
```

**Output attendu (extrait, format complet) :**
```json
{
  "domain": "politique-sociale",
  "geo_scope": "MA",
  "language_mix": ["fr", "ar"],
  "subjects": [
    {
      "id": "s_001",
      "title": "Mobilisation publique des centrales CDT et UMT",
      "angle": "actors",
      "rationale": "Acteurs centraux du blocage. Ton et fréquence des sorties médiatiques sont les indicateurs primaires de la fenêtre de négociation.",
      "sub_queries": [
        { "q": "déclarations CDT UMT réforme code travail 2026", "lang": "fr" },
        { "q": "النقابات المغربية مدونة الشغل 2026", "lang": "ar" },
        { "q": "manifestation Casablanca syndicats avril mai 2026", "lang": "fr" }
      ],
      "rss_keywords": ["cdt", "umt", "syndicats maroc", "code travail"],
      "x_handles_hint": [
        { "handle": "@CDTMaroc", "lang": "fr", "confident": true },
        { "handle": "@UMT_Maroc", "lang": "fr", "confident": true }
      ],
      "reddit_subs_hint": [{ "sub": "morocco", "confident": true }],
      "arxiv_categories_hint": null,
      "expected_signal_volume": "high",
      "confidence": 0.85
    },
    {
      "id": "s_002",
      "title": "Position CGEM et patronat sur la flexibilité CDD",
      "angle": "counter",
      "rationale": "Contrepoids économique structurel. Doctrine claire mais nuances par sous-secteurs (BTP vs services).",
      "sub_queries": [
        { "q": "CGEM réforme code travail position 2026", "lang": "fr" },
        { "q": "patronat marocain flexibilité contrat", "lang": "fr" }
      ],
      "rss_keywords": ["cgem", "patronat maroc"],
      "x_handles_hint": [{ "handle": "@CGEM_Officiel", "lang": "fr", "confident": true }],
      "reddit_subs_hint": null,
      "arxiv_categories_hint": null,
      "expected_signal_volume": "medium",
      "confidence": 0.80
    },
    {
      "id": "s_003",
      "title": "Précédent réforme retraites France 2023 et boomerang social",
      "angle": "precedents",
      "rationale": "Précédent francophone proche, mêmes leviers de mobilisation, leçons sur durée de blocage et coût politique.",
      "sub_queries": [
        { "q": "bilan réforme retraites France 2023 mobilisation", "lang": "fr" },
        { "q": "France pension reform 2023 backlash analysis", "lang": "en" }
      ],
      "rss_keywords": ["retraites france", "pension reform"],
      "x_handles_hint": null,
      "reddit_subs_hint": [{ "sub": "france", "confident": true }],
      "arxiv_categories_hint": null,
      "expected_signal_volume": "medium",
      "confidence": 0.70
    },
    {
      "id": "s_004",
      "title": "Indicateurs chômage jeunes Maroc HCP 2024-2026",
      "angle": "metrics",
      "rationale": "Donnée chiffrée invoquée par les deux camps. Évolution récente HCP cadre la fenêtre politique.",
      "sub_queries": [
        { "q": "HCP taux chômage jeunes Maroc 2026", "lang": "fr" },
        { "q": "البطالة المغرب الشباب 2026", "lang": "ar" }
      ],
      "rss_keywords": ["hcp", "chomage maroc", "emploi jeunes"],
      "x_handles_hint": [{ "handle": "@HCP_MA", "lang": "fr", "confident": true }],
      "reddit_subs_hint": null,
      "arxiv_categories_hint": null,
      "expected_signal_volume": "low",
      "confidence": 0.75
    },
    {
      "id": "s_005",
      "title": "Économie informelle, auto-entrepreneurs et signaux faibles",
      "angle": "weak-signals",
      "rationale": "30% PIB informel. Réforme formelle déplace probablement vers l'informel non-tracé. Sous-couvert mainstream.",
      "sub_queries": [
        { "q": "auto-entrepreneurs Maroc évolution 2026", "lang": "fr" },
        { "q": "économie informelle Maroc impact réforme travail", "lang": "fr" },
        { "q": "informal economy Morocco labor reform", "lang": "en" }
      ],
      "rss_keywords": ["auto-entrepreneur", "informel maroc"],
      "x_handles_hint": null,
      "reddit_subs_hint": [{ "sub": "morocco", "confident": true }],
      "arxiv_categories_hint": null,
      "expected_signal_volume": "low",
      "confidence": 0.55
    },
    {
      "id": "s_006",
      "title": "Vitesse d'adoption parlementaire vs rythme social",
      "angle": "velocity",
      "rationale": "L'écart entre calendrier parlementaire et momentum syndical détermine probabilité d'adoption sans amendement.",
      "sub_queries": [
        { "q": "calendrier parlementaire Maroc projet loi travail 2026", "lang": "fr" },
        { "q": "البرلمان المغربي مدونة الشغل جدول", "lang": "ar" }
      ],
      "rss_keywords": ["parlement maroc", "projet loi"],
      "x_handles_hint": null,
      "reddit_subs_hint": null,
      "arxiv_categories_hint": null,
      "expected_signal_volume": "low",
      "confidence": 0.65
    }
  ],
  "tensions": [
    {
      "between": ["s_001", "s_002"],
      "nature": "Lecture des mêmes données chômage par syndicats vs patronat aboutit à conclusions inverses sur flexibilité.",
      "exploit_in_synthesis": true
    },
    {
      "between": ["s_004", "s_005"],
      "nature": "Statistiques HCP officielles vs réalité informelle peuvent diverger fortement.",
      "exploit_in_synthesis": true
    }
  ],
  "blind_spots": [
    {
      "description": "Voix arabophones populaires (forums, talk-shows TV arabes) sous-représentées dans flux RSS francophones.",
      "mitigation_query": "تعليقات المغاربة على إصلاح مدونة الشغل"
    },
    {
      "description": "Position des grandes entreprises étrangères (Renault, Stellantis, OCP fournisseurs) rarement publique.",
      "mitigation_query": "Renault Tanger Maroc politique sociale 2026"
    }
  ],
  "recursion_budget": 1
}
```

### Few-shot 2 — produit consumer Europe (FR)

**Input :**
```json
{
  "seed": "Lancement biscuit halal Auchan en France ciblant les communautés MENA, packaging FR/AR, distribution magasins urbains Île-de-France et Lyon.",
  "lang": "fr",
  "sector_hint": "retail"
}
```

**Output attendu (résumé) :**
```json
{
  "domain": "produit-consumer",
  "geo_scope": "EU",
  "language_mix": ["fr", "ar", "en"],
  "subjects": [
    { "id": "s_001", "title": "Concurrence directe sur le marché halal France (Isla Délice, Médina, Reghalal)", "angle": "actors", ... },
    { "id": "s_002", "title": "Chiffres consommation halal France INSEE/IFOP 2024-2026", "angle": "metrics", ... },
    { "id": "s_003", "title": "Précédents lancements halal grande distribution (Carrefour Halal, Lidl)", "angle": "precedents", ... },
    { "id": "s_004", "title": "Signaux faibles communautés franco-marocaines/algériennes/tunisiennes (TikTok, forums)", "angle": "weak-signals", ... },
    { "id": "s_005", "title": "Position acteurs religieux et certificateurs halal France (Mosquée Paris, AVS)", "angle": "counter", ... }
  ],
  "tensions": [{ "between": ["s_004", "s_005"], "nature": "Communautés diaspora pragmatiques vs certificateurs formels strict.", "exploit_in_synthesis": true }],
  "blind_spots": [{ "description": "Voix communautaires arabophones diaspora absentes des flux mainstream FR.", "mitigation_query": "حلال أوشان فرنسا" }],
  "recursion_budget": 1
}
```

---

## PROMPT 2 — `rubric-architect`

**Task Kairos** : `enrichment`
**Tier suggéré** : rapide (génération structurée).
**Rôle** : génère une rubric de scoring **+ disqualifiers durs + soft boosts**, pas une simple grille pondérée.

### Système

```
Tu génères une rubric de scoring TROIS-COUCHES pour évaluer la pertinence
de signaux d'actualité par rapport à une graine de réalité ET sa
research_strategy (output Prompt 1).

LES TROIS COUCHES :

1. CRITERIA — pondération additive (somme = 100). Score continu sur chaque
   critère, agrégé.

2. DISQUALIFIERS — règles binaires. Un signal qui matche un disqualifier
   est SCORE = 0 immédiatement, indépendamment des criteria. Exemples :
   "promotionnel pur sans fait", "opinion sans source", "horoscope/buzz",
   "off-topic géographique total".

3. SOFT_BOOSTS — bonus appliqués APRÈS calcul criteria, capped. Exemples :
   "+15 si signal contredit la lecture dominante", "+10 si signal en
   langue minoritaire du dossier (ex: AR pour un sujet MENA)", "+5 si
   source primaire (acteur lui-même) vs commentateur".

POURQUOI CETTE STRUCTURE :
- Criteria seuls produisent un mid-tier confortable mais pas
  actionnable. Les disqualifiers nettoient le bruit. Les soft_boosts
  remontent les signaux à valeur surprise (counter-narrative,
  multilingue, primaire) qui sont les plus utiles à la simulation
  prospective en aval.

RÈGLES :
- Langue {{lang}}. FR : accents majuscules obligatoires.
- 4-8 criteria adaptatifs (selon complexité de la graine). Somme = 100
  exactement. Hiérarchie visible (au moins un poids ≥ 25, au moins un ≤ 10).
- 3-6 disqualifiers. Formuler en règles testables par un LLM rapide
  ("le signal est-il purement promotionnel sans donnée?").
- 2-5 soft_boosts. Plafonner chaque à +20 max, total < +50.
- INTERDIT : critères vagues ("intérêt", "qualité"), critères qui se
  chevauchent ("pertinence" et "rapport au sujet"), pondération
  uniforme.
- Le scoring_prompt (200-500 mots) doit RÉCAPITULER les 3 couches
  pour le LLM scoreur, et donner 2-3 exemples calibrés (un signal
  qui mérite 80+, un autour de 40, un autour de 10).

SCHEMA OUTPUT :
{
  "scoring_prompt": "string 200-500 mots — instructions au scoreur en {{lang}}",
  "criteria": [
    ["label_court", weight_int],
    ...
  ],
  "disqualifiers": [
    { "id": "dq_001", "rule": "string règle testable", "rationale": "string courte" }
  ],
  "soft_boosts": [
    { "id": "sb_001", "rule": "string règle", "boost": int, "rationale": "string courte" }
  ],
  "calibration_examples": [
    { "expected_score": 85, "signal_archetype": "string description signal" },
    { "expected_score": 40, "signal_archetype": "string description signal" },
    { "expected_score": 10, "signal_archetype": "string description signal" }
  ]
}

SOMME DES weight DOIT FAIRE EXACTEMENT 100. Validé en post-process,
sinon retry du prompt.
```

### Few-shot — politique MA (FR)

**Input :**
```json
{
  "seed": "Réforme du Code du travail au Maroc en 2026...",
  "lang": "fr",
  "research_strategy": { "...": "extrait Prompt 1 ci-dessus" }
}
```

**Output attendu :**
```json
{
  "scoring_prompt": "Tu es un analyste qui évalue la pertinence d'un signal d'actualité (article, post X, thread Reddit) par rapport à un sujet d'étude prospective : la réforme du Code du travail au Maroc en 2026, dans un contexte de tension entre la CGEM et les syndicats CDT-UMT. La rubric a TROIS couches. (1) Score continu de 0 à 100 sur 5 critères pondérés (somme=100). (2) DISQUALIFIERS qui mettent à 0 si match. (3) SOFT_BOOSTS qui ajoutent jusqu'à +40 max après le score continu. Concentre-toi sur la pertinence concrète : un signal vague qui mentionne 'travail' sans rapport vaut 10. Un signal précis qui cite la CGEM ou un syndicat avec une donnée chiffrée vaut 80+. Un signal en arabe d'un militant CDT mérite +10 boost (langue minoritaire). Un signal qui contredit la position du gouvernement mérite +15 boost (counter). Privilégie les signaux datés < 6 mois. Justifie en 1-2 phrases ton score final, en mentionnant si un disqualifier ou un boost s'est appliqué.",
  "criteria": [
    ["topical_match_reforme_travail", 30],
    ["actor_relevance_cgem_syndicats_etat", 25],
    ["data_or_decision_concrete", 20],
    ["temporal_recency_6_mois", 15],
    ["geographic_focus_maroc", 10]
  ],
  "disqualifiers": [
    { "id": "dq_001", "rule": "Le signal est purement promotionnel (pub, marketing employeur) sans aucune donnée factuelle.", "rationale": "Pollue le scoring sans valeur prospective." },
    { "id": "dq_002", "rule": "Le signal traite du Code du travail d'un autre pays sans aucune mention/comparaison Maroc.", "rationale": "Hors scope." },
    { "id": "dq_003", "rule": "Le signal est un horoscope, divertissement, sport, célébrité.", "rationale": "Bruit total." },
    { "id": "dq_004", "rule": "Le signal date de plus de 18 mois et n'est pas un précédent historique structurant.", "rationale": "Données obsolètes biaisent le modèle." }
  ],
  "soft_boosts": [
    { "id": "sb_001", "rule": "Signal en langue arabe traitant du sujet (acteur arabophone, opinion populaire).", "boost": 10, "rationale": "Compense le biais francophone du flux RSS dominant." },
    { "id": "sb_002", "rule": "Signal contredit la lecture dominante syndicale ou patronale (point de vue divergent).", "boost": 15, "rationale": "Counter-narrative = matière première de simulation prospective." },
    { "id": "sb_003", "rule": "Source primaire (acteur s'exprime directement : compte X officiel, communiqué CGEM, déclaration syndicat).", "boost": 8, "rationale": "Authenticité supérieure aux commentateurs." },
    { "id": "sb_004", "rule": "Signal d'un secteur informel ou auto-entrepreneur (signal faible).", "boost": 7, "rationale": "Comble le blind-spot identifié dans research_strategy." }
  ],
  "calibration_examples": [
    { "expected_score": 90, "signal_archetype": "Tweet @CDTMaroc en FR/AR datant d'il y a 2 jours, citant un chiffre HCP précis et appelant à grève le 15 mai 2026." },
    { "expected_score": 45, "signal_archetype": "Article presse FR généraliste qui mentionne la réforme en passant dans un papier sur l'économie marocaine, sans acteur identifié." },
    { "expected_score": 5, "signal_archetype": "Article promotionnel d'un cabinet RH vantant ses services de recrutement post-réforme." }
  ]
}
```

---

## PROMPT 3 — `signal-synthesizer`

**Task Kairos** : `enrichment`
**Tier suggéré** : raisonnement (clustering + génération briefs structurés).
**Rôle** : transforme les signaux scorés en topics avec **briefs multi-versions, tensions internes explicitées, coverage map, devil's advocate forcé**.

### Système

```
Tu reçois 30-80 signaux SCORÉS (id, titre, URL, source, lang, score 0-100,
extrait court 200 chars, disqualified: bool, applied_boosts: [string]).
Tu reçois aussi la research_strategy (subjects, tensions, blind_spots).

Ta MISSION : transformer ce matériau brut en TOPICS exploitables par
Bassira pour générer des simulations prospectives multi-agents.

UN TOPIC RICHE EN PROSPECTIVE A 4 PROPRIÉTÉS :
1. UN CLUSTER COHÉRENT de signaux (≥ 3, sauf devil's advocate qui peut
   être moins).
2. UNE TENSION INTERNE ou un GAP ASSUMÉ (les signaux ne sont pas tous
   d'accord, ou il manque un acteur clé). Les topics tout-convergents
   sont des culs-de-sac.
3. UN BRIEF en 1-3 VARIANTES (frames différents : market, decision,
   crisis, policy, cerberus). Chaque variante simulable indépendamment
   avec un framework Bassira approprié.
4. UNE PROVENANCE TRACÉE : key_signals supporting, key_signals
   conflicting, et un confidence calibré.

ÉTAPES OBLIGATOIRES :

1. Filtre : ignore les signaux avec disqualified=true. Ils ne servent
   pas au clustering.

2. Clusterise sémantiquement les signaux retenus. Adaptatif :
   - 3-8 topics MACRO.
   - Si un topic macro contient ≥ 8 signaux, propose 2-3 sub-topics.

3. Pour chaque topic, identifie EXPLICITEMENT :
   - les signaux qui SUPPORTENT le narratif principal du cluster.
   - les signaux qui CONTREDISENT ou nuancent.
   Si aucun signal ne contredit dans le cluster, regarde dans les
   AUTRES topics si un signal d'un cluster voisin contredit. Référence
   par cross_topic_conflicts.

4. Génère 1-3 BRIEF VARIANTS par topic. Règles brief :
   - 250-400 caractères stricts (espaces inclus).
   - Question simulable avec horizon temporel explicite.
   - 2-4 acteurs identifiables nommés.
   - Seuil quantifiable si possible (taux, montant, %, date).
   - Commence par le scénario, jamais par "Le sujet de" ou "Étudions".
   - Frame différent par variante (market vs decision vs crisis...).

5. FORCE ≥ 1 topic "devil's advocate" : un topic qui ARGUMENTE LE
   CONTRAIRE de la lecture dominante de la graine. Même avec peu de
   signaux. Tag explicite : type="devil_advocate". Le brief de ce
   topic doit poser la question dans le sens opposé du seed
   (ex: si seed parle d'une réforme imminente, le devil's advocate
   demande "que se passe-t-il si la réforme est repoussée 18 mois ?").

6. COVERAGE MAP : pour chaque subject de la research_strategy, indique
   nombre de signaux retenus. Si un subject a 0 signaux, c'est un
   GAP qui peut déclencher iterative-deepening.

7. CULTURAL CHECK : si language_mix attendu était {fr, ar, en} mais
   100% des signaux retenus sont fr → flag dans cultural_warnings.

INTERDICTIONS :
- Inventer un signal_id absent de l'input.
- Mettre en key_signals_supporting plus de 6 ids (resté en focus).
- Brief hors longueur 250-400.
- Brief en langue ≠ {{lang}}.
- Brief copy-collé à la graine.
- Topic mono-source (tous les signaux d'un cluster viennent de la
  même source) → flag mono_source_warning.

SCHEMA OUTPUT :
{
  "topics": [
    {
      "id": "t_001",
      "label": "5-15 mots",
      "summary": "30-60 mots",
      "type": "regular|devil_advocate|emerging",
      "dominant_angle": "actors|metrics|...",
      "key_signals_supporting": ["sig_xx", "sig_yy", "sig_zz"],
      "key_signals_conflicting": ["sig_aa"] | [],
      "cross_topic_conflicts": [{"topic_id": "t_005", "signal_id": "sig_bb"}] | [],
      "internal_tension": "string 15-30 mots décrivant la tension interne au cluster" | null,
      "brief_variants": [
        {
          "framework_hint": "cerberus|market|decision|crisis|policy",
          "brief": "string 250-400 chars",
          "rationale": "10-20 mots — pourquoi ce frame ici"
        }
      ],
      "provenance": {
        "lang_distribution": {"fr": 5, "en": 2, "ar": 1},
        "source_diversity_score": 0.0-1.0,
        "freshness_median_days": int
      },
      "confidence": 0.0-1.0,
      "warnings": ["mono_source_warning", "low_signal_count", ...]
    }
  ],
  "coverage_map": {
    "s_001": { "signals_count": 12, "covered": true, "topics": ["t_001", "t_003"] },
    "s_002": { "signals_count": 0, "covered": false, "topics": [] },
    ...
  },
  "cultural_warnings": [
    "Aucun signal en arabe alors que la research_strategy demandait fr+ar."
  ],
  "devil_advocate_topic_id": "t_007"
}
```

---

## PROMPT 4 — `quality-auditor`

**Task Kairos** : `enrichment`
**Tier suggéré** : rapide (vérification structurée multi-axes).
**Rôle** : audit MULTI-DIMENSIONS de l'output complet (Prompt 1+2+3) avant retour à Bassira. Peut **déclencher iterative-deepening** sur gaps.

### Système

```
Tu es un auditeur de chaîne de recherche prospective. Tu reçois l'output
COMPLET du pipeline (research_strategy + rubric + topics + coverage_map +
cultural_warnings). Tu ne refais pas le travail : tu détectes les défauts
et décides si une seconde passe (iterative-deepening) est nécessaire.

7 AXES D'AUDIT :

1. HALLUCINATION : tout signal_id mentionné en topic.key_signals existe-t-il
   dans l'input ? Tout x_handle ou source citée existe-t-il réellement ?
   Toute donnée chiffrée invoquée est-elle attribuée à une source ?

2. COUVERTURE : combien de subjects de la research_strategy n'ont produit
   AUCUN signal retenu ? Si > 30% des subjects sont sans couverture,
   c'est un FAIL.

3. ÉQUILIBRE LINGUISTIQUE : si language_mix demandait fr+ar+en mais que
   90%+ des signaux retenus sont fr, c'est un cultural blind-spot.

4. NOVELTY : les topics répètent-ils la graine ou apportent-ils des angles
   non évidents ? Un topic qui paraphrase la graine = échec novelty.

5. ACTIONABILITY : les briefs sont-ils simulables ou trop vagues ? Test :
   un brief actionnable nomme acteurs+horizon+seuil. Un brief vague dit
   "étudions les conséquences".

6. BIAS / TONE : un topic charge-t-il un acteur sans contre-équilibre ?
   Un brief contient-il un jugement de valeur ("scandaleux",
   "irresponsable") ? Audit politique strict.

7. ENGAGEMENT DEVIL'S ADVOCATE : le devil_advocate_topic est-il présent
   ET réellement contraire à la lecture dominante ? Pas un topic
   "neutre" déguisé.

VERDICTS :
- "pass" : aucune issue high. Output retourné tel quel.
- "warn" : 1-3 issues medium, aucune high. Output retourné avec flag,
  loggué pour monitoring.
- "fail" : 1+ issue high SANS solution recommandée. Output dégradé,
  Bassira affiche "qualité dégradée".
- "deepen" : 1+ issue high AVEC une solution claire = un gap précis.
  Trigger Prompt 5 (iterative-deepening) avec le gap en input.

SCHEMA OUTPUT :
{
  "verdict": "pass|warn|fail|deepen",
  "issues": [
    {
      "axis": "hallucination|coverage|linguistic|novelty|actionability|bias|devil_advocate",
      "severity": "high|medium|low",
      "location": "topic.t_001.brief_variants[0]|coverage_map.s_004|...",
      "description": "string 15-40 mots",
      "fix_action": "auto_correct|trigger_deepening|warn_user|none",
      "auto_correction": "string ou null"
    }
  ],
  "auto_corrections_applied": {
    "topic.t_001.brief_variants[0]": "version corrigée"
  },
  "deepening_targets": [
    {
      "type": "uncovered_subject|cross_topic_conflict|cultural_blindspot",
      "context": "string 20-50 mots — quoi re-chercher",
      "suggested_sub_seed": "string sub-seed à passer à Prompt 5"
    }
  ]
}
```

### Quand déclencher iterative-deepening (decision tree)

| Cas | Verdict | Action |
|---|---|---|
| Tout est nickel | `pass` | Return |
| 1 brief mal formaté, auto-correctable | `warn` | Auto-correct, return |
| 1 subject sans signal mais topic robuste ailleurs | `warn` | Return + flag |
| ≥ 30% subjects non couverts | `deepen` | Prompt 5 sur subjects manquants |
| Aucun devil's advocate ou faux devil's advocate | `deepen` | Prompt 5 forcé contraire |
| 90%+ signaux mono-langue alors que mix attendu | `deepen` | Prompt 5 sur langue manquante |
| Hallucination détectée (signal_id inexistant) | `fail` | Return dégradé sans deepening (incident) |
| 2 issues high différentes | `fail` | Return dégradé + log alert |

---

## PROMPT 5 — `iterative-deepening`

**Task Kairos** : `enrichment`
**Tier suggéré** : raisonnement.
**Rôle** : prend un GAP identifié par l'auditor et génère un **sub-seed** scopé qui re-traverse le pipeline (depth+1, max=2).

### Système

```
Tu reçois :
- la graine ORIGINALE
- la research_strategy initiale
- un GAP identifié (uncovered_subject | cross_topic_conflict |
  cultural_blindspot)
- les topics déjà produits
- la depth actuelle (0 ou 1)

Ta mission : formuler un SUB-SEED qui zoome sur le gap et re-déclenche
le pipeline complet (Prompts 1→4) avec un focus serré.

PRINCIPES :
- Le sub-seed est PLUS NARROW que la graine originale, JAMAIS plus large.
- Le sub-seed cite explicitement les acteurs/concepts/langues à
  privilégier dans cette nouvelle passe.
- Les sub-queries proposées contournent les sources déjà épuisées
  (proposer X au lieu de RSS si RSS a saturé, ou inverse).
- Si depth_actuelle == 1, c'est la DERNIÈRE passe possible. Le sub-seed
  doit être maximalement spécifique.
- Si le gap est cultural_blindspot AR, le sub-seed PEUT être en AR
  même si le seed original était en FR (Kairos gère, le merge final
  traduit dans la lang de sortie).

ANTI-PATTERN À ÉVITER :
- Re-générer la graine originale en la paraphrasant. Inutile.
- Demander des "informations générales sur X". Trop vague.
- Élargir le scope ("ajoutons aussi le contexte africain"). Hors mission.

SCHEMA OUTPUT :
{
  "sub_seed": "string 100-300 chars — la sous-graine cadrée",
  "focus_lang": "fr|en|ar",
  "force_subjects_count": 2|3,
  "force_angles": ["counter", "weak-signals", ...],
  "exclude_sources_used": ["rss"|"x"|"reddit"|"arxiv"] | [],
  "merge_strategy": "append|replace_subject_id_xxx|merge_into_topic_t_yyy",
  "rationale": "20-40 mots — pourquoi ce sub-seed pour ce gap"
}
```

### Few-shot — gap cultural_blindspot AR

**Input :**
```json
{
  "original_seed": "Réforme Code du travail Maroc 2026...",
  "gap": {
    "type": "cultural_blindspot",
    "context": "Aucun signal en arabe parmi 47 retenus, alors que research_strategy demandait fr+ar."
  },
  "current_depth": 0
}
```

**Output :**
```json
{
  "sub_seed": "Opinions arabophones populaires sur la réforme du Code du travail au Maroc 2026 : forums marocains en darija, talk-shows TV arabes, déclarations de syndicalistes arabophones, militants associatifs.",
  "focus_lang": "ar",
  "force_subjects_count": 3,
  "force_angles": ["actors", "weak-signals", "counter"],
  "exclude_sources_used": ["arxiv"],
  "merge_strategy": "append",
  "rationale": "Compense le déséquilibre francophone du 1er pass en forçant des sources arabophones ciblées sur les voix populaires non médiatisées."
}
```

### Bornes de récursion

- `current_depth = 0` → Prompt 5 peut générer 1 sub-seed → re-pipeline → final merge.
- `current_depth = 1` → Prompt 5 peut générer encore 1 sub-seed → re-pipeline → final merge.
- `current_depth = 2` → JAMAIS appelé. Pipeline retourne avec verdict actuel + flag depth_exhausted.

Coût total max par recherche : 1 + 2 = 3 passes du pipeline complet. Cache de chaque sub-pass à part (sha256(sub_seed+lang)).

---

## Tests de validation Phase 0

7 graines test variées à passer manuellement contre les 4 prompts (1→4 sans deepening pour garder Phase 0 simple) :

1. **Politique MA** : "Réforme du Code du travail au Maroc en 2026..." (cas FR utilisé en few-shot)
2. **Marketing FR** : "Lancement biscuit halal Auchan en France ciblant communautés MENA"
3. **Crise sanitaire MENA** : "Émergence variant grippal H5N1 en Égypte, propagation MENA"
4. **Finance** : "IPO Banque Centrale Populaire Bourse Casablanca, valorisation 80 Mds MAD"
5. **Cyber** : "Attaque ransomware OCP Group, négociation rançon, impact production phosphates"
6. **Tech / scientifique** : "Adoption agents IA en cabinets juridiques européens 2026" (test ArXiv hint)
7. **Géopolitique multi-langue** : "Tensions Algérie-Maroc autour gaz Maghreb-Europe pipeline 2026" (force ar+fr+en)

**Critères d'acceptation Phase 0 :**

- [ ] 7/7 outputs Prompt 1 ont 3-12 subjects adaptatifs (pas un quota fixe)
- [ ] 7/7 outputs Prompt 1 ont ≥ 1 tension explicite ET ≥ 1 blind_spot
- [ ] Au moins 4/7 outputs Prompt 1 ont language_mix multilingue
- [ ] 7/7 outputs Prompt 2 ont somme criteria = 100, ≥ 3 disqualifiers, ≥ 2 soft_boosts
- [ ] 7/7 outputs Prompt 3 ont ≥ 1 devil_advocate_topic correctement contraire
- [ ] 7/7 outputs Prompt 3 ont brief_variants entre 250-400 chars stricts
- [ ] 7/7 outputs Prompt 3 ont coverage_map pour CHAQUE subject
- [ ] 7/7 outputs Prompt 4 produisent un verdict cohérent (pas tout pass, pas tout fail)
- [ ] FR : 100% accents majuscules présents
- [ ] 0 occurrence `<tool_call>`, `<thinking>`, balise XML
- [ ] Tests fail rate < 30% des cas → si > 30% on retourne aux prompts

## Décisions ouvertes

- [ ] **Streaming SSE** Kairos→Bassira ? V1 one-shot, V2 SSE.
- [ ] **Cache TTL** seed-to-research_strategy : 24h vs 7j ? (graines évoluent, signaux sont le facteur volatil).
- [ ] **Quality auditor critical path V1** ou monitoring async ? Recommandation V1 critical path activé pour `deepen` uniquement, `pass/warn/fail` retourné direct.
- [ ] **Iterative-deepening** : on l'active dès V1 ou on commence sans (V1 simple linéaire pour POC, V2 ajoute deepening) ?
- [ ] **Mapping `task` Kairos** : nouvelle task `research` dans `model_config` ou réutiliser `enrichment` ? Recommandation : créer `research` pour permettre routage BYOK distinct.
- [ ] **Budget garde-fou** : `settings.daily_budget_usd` Kairos pour le tenant Bassira-bot, ou un compteur dédié `bassira_research_budget` ?
- [ ] **Multi-version brief** : on retourne 1-3 variants à Bassira et le user choisit, OU on retient 1 best-pick automatique ? Recommandation : 1-3 variants côté API, UI Bassira décide d'afficher 1 ou plusieurs.

## Stories Ralph swarm — découpage Phase 1+ révisé

| Story | Codebase | Effort solo | Phase swarm |
|---|---|---|---|
| K01 | Kairos — `research-strategist` edge fn + tests | 5h | Phase 1 ★ |
| K02 | Kairos — `rubric-architect` edge fn + tests | 4h | Phase 1 ★ |
| K05 | Kairos — `signal-synthesizer` edge fn + tests | 7h | Phase 1 ★ |
| K07 | Kairos — `quality-auditor` edge fn + tests | 4h | Phase 1 ★ |
| K03 | Kairos — `signals_session` table + TTL cron + adapt scrapers | 4h | Phase 2 |
| K04 | Kairos — `llm-score-batch` accepte rubric_override + disqualifiers + soft_boosts | 5h | Phase 2 |
| K08 | Kairos — `iterative-deepening` edge fn + recursion bornée | 5h | Phase 2 (V2 si V1 sans) |
| K06 | Kairos — orchestratrice `research-from-seed` + public_api_keys + CORS | 6h | Phase 2 (après K01-05-07) |
| B01 | Bassira — `/api/research/from-seed` proxy + cache + fallback + tests | 4h | Phase 3 |
| B02 | Bassira — `TopicResearchPanel.vue` (refonte TrendingTopics) avec brief variants picker | 7h | Phase 3 |
| B03 | Bassira — Hook ConsoleView debounce + tests E2E | 3h | Phase 3 |

★ Phase 1 : 4 prompts indépendants (chacun appelle `dispatch-llm`, retourne JSON). Aucune dépendance croisée. 4 sub-agents parallèles.

**Chrono mur Ralph swarm V1 (sans deepening)** : ~3h-3h30.
**Chrono mur Ralph swarm V2 (avec deepening K08)** : ~3h30-4h.

## Notes opérationnelles

- Prompts stockés Kairos `supabase/functions/_shared/prompts/{research-strategist, rubric-architect, signal-synthesizer, quality-auditor, iterative-deepening}.md`.
- Header YAML : `version: 1.0.0` + `task: enrichment` + `tier_hint: rapide|raisonnement` + `last_modified: YYYY-MM-DD`. Aucun modèle. Le user décide via `model_config[task]`.
- Telemetry : log chaque appel dans `llm_costs(task, model_resolved, tokens, cost, latency_ms, session_id, depth)`.
- Feedback loop : table `topic_feedback(session_id, topic_id, brief_variant_idx, vote: +1|-1, ts)` pour itérer prompts à terme.
- Sanitisation Kairos : `sanitize_llm_output` purge balises XML / tool_call / thinking AVANT retour Bassira, jamais en supposant que le modèle obéit (critique BYOK).
- Cache : `seed-to-research_strategy` 24h, `rubric-architect` 24h (lié au seed), `signals-to-topics` aucun cache (signaux changent), audit aucun cache.
- Budget per recherche : monitoring `llm_costs.cost` agrégé par session. Garde-fou Coolify env var (à décider).
