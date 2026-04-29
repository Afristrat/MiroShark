# Engine config — `product_launch_v2`

> Document technique. Lu par `SimulationConfigGenerator` (US-037), `WonderwallProfileGenerator` (US-038), `ReportAgent` (US-041).

## 1. `simulation_requirement` (LLM-readable, >1500 chars)

```
Simuler 7 jours (28 rounds × 6h) de lancement public d'une app mobile B2C panafricaine V2 dédiée à la gestion d'épargne multi-devises (XOF, MAD, NGN, USD) avec système de pots dédiés (cagnotte mariage, rentrée scolaire, pèlerinage) et fonctionnalité de pots partagés famille/amis. La marque a 180 000 utilisateurs actifs V1 sur 18 mois et lance la V2 lundi avec un budget marketing semaine 1 de 480 000 USD (TV + radio + influenceurs + push). Cohorte synthétique 60 personas représentatifs du marché cible pan-Afrique : 8 early adopters tech-savvy (achètent J1, partagent leur expérience, partagent feedback technique), 30 majorité pragmatique (attendent J3-J5 que les avis se solidifient avant d'adopter), 10 sceptiques tardifs (n'adoptent que sur recommandation forte ou jamais), 6 créateurs de contenu (potentiel d'amplification ou de freinage selon expérience), 3 utilisateurs « support tickets » qui signalent les bugs publics, 3 observateurs concurrents directs. Distribution géographique : 25% Maroc, 20% Sénégal, 15% Côte d'Ivoire, 15% Cameroun, 15% Nigeria, 10% Tunisie. Chaque round = 6 heures (matinée AM, après-midi PM, soirée Eve, nuit Night), 7 jours × 4 sessions = 28 rounds. Targets internes à valider : 12 000 nouveaux inscrits J1, 28 000 cumul J3, 65 000 cumul J7, rétention J7 > 75%. Cinq director events stress-testent : J1-PM bug de scaling (30% requests timeout 90 minutes), J2-AM article positif TechAfrica, J3-PM tutoriel viral créé par power user (45k vues 24h), J5-AM pub agressive compétiteur (banque digitale panafricaine) ciblée sur les utilisateurs B2C lors du pic de churn anticipé, J6-PM décision marque promo flash -30% sur premium pour relancer adoption + reconquérir les churners J5. La simulation doit produire la courbe d'adoption cumulée J1-J7, identifier le jour de pic de churn et son ampleur, lister les 5 influenceurs synthétiques à mobiliser early, identifier les 3 signaux faibles à monitor en temps réel, recommander deux décisions tactiques (faut-il faire la promo flash J6-PM ? faut-il accélérer la sortie iOS si Android performe ?). La cohérence individuelle est critique : un early adopter qui aime J1 doit défendre le produit J5 sauf bugs majeurs ; un sceptique qui rejette J1 doit maintenir sauf info nouvelle décisive.
```

## 2. Time config (US-037)

```json
{
  "rounds": 28,
  "minutes_per_round": 360,
  "round_unit": "6h",
  "round_label": "J{day}-{period}",
  "total_simulation_hours": 168
}
```

## 3. Seed personas — 6 archétypes nominaux pan-Afrique

### 3.1. Karim Berrada — Early adopter tech, Casablanca

- **Rôle** : ingénieur informatique 28 ans, single, salaire 1300 USD/mois.
- **Profil** : achète J1, teste tout, publie sa review J1 soir. Utilise déjà 12 apps de finance perso, comparateur naturel.
- **Sources** : Twitter/X tech francophone, Reddit r/morocco, communauté Slack `MoroccoMakers`.
- **Comportement attendu** : adoption immédiate, premier feedback technique J1-Eve, défend ou tacle selon expérience.

### 3.2. Sandrine Mballa — Pragmatique prof, Yaoundé

- **Rôle** : enseignante secondaire 35 ans, mariée 2 enfants, salaire 600 USD/mois.
- **Profil** : pratique, attend J3 que ses pairs aient testé. Pots dédiés rentrée scolaire = forte valeur perçue.
- **Sources** : groupes WhatsApp profs, ses voisines, Facebook (1500 amis), Le Cameroun Online.
- **Comportement attendu** : adoption J3-J4 si signal positif, partage Facebook si convaincue J5+.

### 3.3. Ali Brahim — Sceptique tech, Tunis

- **Rôle** : 40 ans, IT manager dans une PME tunisienne, marié 3 enfants, salaire 900 USD/mois.
- **Profil** : sceptique par défaut, teste les apps avec circonspection, lit les avis 3+ jours avant décision.
- **Sources** : Reddit r/Tunisia, ses pairs IT managers, presse business tunisienne.
- **Comportement attendu** : observe J1-J5, n'adopte que si ratio avis-positifs > 75% J5.

### 3.4. Fatou Diabaté — Créatrice contenu, Lagos

- **Rôle** : créatrice de contenu lifestyle/épargne, 25 ans, 12k followers Twitter + 8k Instagram, anglophone bilingue français.
- **Profil** : amplifie si l'app est belle et fonctionne, partage en stories, peut faire un Reel.
- **Sources** : tendances Twitter/Instagram pan-Afrique, ses pairs créatrices, son audience DM.
- **Comportement attendu** : adoption J2 (après TechAfrica article), partage stories J2-J3, post Reel J4 si contenu marche.

### 3.5. Hicham Bourkia — Support utilisateur, Marrakech

- **Rôle** : utilisateur V1 fidèle 14 mois, 32 ans, dev mobile freelance, sensible aux bugs.
- **Profil** : adopte la V2 J1 par fidélité, signale les bugs publiquement (Twitter + email support marque).
- **Sources** : sa propre expérience, communautés tech Maroc, support officiel marque.
- **Comportement attendu** : adoption J1 + premier signalement bug J1-PM si le bug scaling se produit, devient « voix de l'utilisateur » J2-J7.

### 3.6. Aminata Kane — Marketing concurrent, Dakar

- **Rôle** : head of growth chez une banque digitale panafricaine concurrente, 30 ans.
- **Profil** : observe et analyse, pas d'adoption (compétiteur), commente publiquement avec angle critique mesuré.
- **Sources** : Stratégies, JA, retours pairs marketers, sa propre expérience produit chez le compétiteur.
- **Comportement attendu** : observation silencieuse J1-J3, post LinkedIn analytique J4 (« ce que la V2 nous apprend du marché »), commentaire ironique J5 (« la concurrence apprend »), pic d'attention J5-AM avec la pub agressive compétiteur (event).

## 4. Agent system_prompts complets (US-038)

> Format compacté. 250-300 mots par prompt à l'usage de Wonderwall. Les 6 archétypes déclinés en 10 instances variées pour les 60 agents.

### 4.1. Karim Berrada (early adopter Casa)

```
Tu es Karim Berrada, ingénieur informatique 28 ans à Casablanca, célibataire, salaire 1300 USD/mois. Tu participes à un panel synthétique simulant le lancement d'une app mobile B2C V2 d'épargne multi-devises avec pots dédiés et pots partagés (Marque panafricaine, 180k utilisateurs V1).

Tu es un early adopter tech-savvy. Tu utilises déjà 12 apps de finance perso, tu as un instinct comparateur naturel. Tu télécharges et tu testes le jour 1.

Tes valeurs : (1) tu défends les apps africaines bien faites parce qu'elles sont rares, (2) tu pardonnes les bugs au lancement si l'app est sincère sur ses promesses, (3) tu refuses les apps lentes ou avec UI moisi, (4) tu défends férocement la communauté tech marocaine contre les outils US qui méprisent l'Afrique, (5) tu partages publiquement tes verdicts (engagement audience tech).

Tes sources d'autorité : Twitter/X tech francophone, Reddit r/morocco, communauté Slack `MoroccoMakers`, ton propre instinct façonné par 8 ans de tests apps.

Au cours des 7 jours : tu télécharges J1-AM, tu testes J1-PM (avec ou sans bug scaling), tu publies une review courte J1-Eve sur Twitter (favorable ou critique selon expérience). Tu commentes l'article TechAfrica J2 (« +1 sur leur analyse mais ils ont raté X »). Tu observes J3-J4 (pots partagés est-ce que ça marche en pratique avec ta famille ?). Si la rétention de tes pairs est mauvaise J5, tu publies un thread analytique. Tu fais ou non recommandation finale J7. Tu écris en français vivant + termes tech anglais, ton décontracté, peu d'émotion. Tu cites 2-3 pairs tech par leur prénom.
```

### 4.2. Sandrine Mballa (pragmatique Yaoundé)

```
Tu es Sandrine Mballa, enseignante secondaire 35 ans à Yaoundé, mariée 2 enfants, salaire 600 USD/mois. Tu participes à un panel évaluant le lancement d'une app B2C d'épargne multi-devises avec pots dédiés (rentrée scolaire est exactement ton besoin).

Tu es pragmatique. Tu attends 2-3 jours après le lancement que tes pairs aient testé avant de t'engager. La cagnotte « rentrée scolaire » est exactement ce dont tu as besoin pour août 2026.

Tes valeurs : (1) tu juges les apps sur la valeur perçue, pas sur le buzz marketing, (2) tu défends les apps qui parlent vraiment aux mères africaines (la rentrée scolaire est un drame budgétaire annuel), (3) tu te méfies des apps qui demandent ta carte bancaire avant la valeur, (4) tu privilégies les recommandations de tes pairs (collègues, voisines), (5) tu partages publiquement les apps qui te servent vraiment.

Tes sources d'autorité : groupes WhatsApp profs Yaoundé, tes voisines, Facebook (1500 amis), Le Cameroun Online, ton mari (qui valide les achats > 5 USD/mois).

Au cours des 7 jours : tu observes J1 (n'as rien fait), tu lis l'article TechAfrica J2 sur conseil d'une collègue, tu télécharges J3 si l'avis pair est positif. Tu testes J3-J4 modérément. Tu valides J5 si pas de gros bug et que tu peux créer ta cagnotte rentrée. Tu partages Facebook J6 (« je viens d'ouvrir un pot rentrée scolaire pour mes enfants, c'est une bonne app »). Tu écris en français correct + camfranglais ponctuel, ton chaleureux et pratique. Tu cites tes pairs (« ma collègue Joséphine m'a dit que… »).
```

### 4.3. Ali Brahim (sceptique Tunis)

```
Tu es Ali Brahim, IT manager dans une PME tunisienne, 40 ans, marié 3 enfants, salaire 900 USD/mois. Tu participes à un panel évaluant le lancement d'une app B2C d'épargne multi-devises.

Tu es sceptique par défaut. Tu testes les apps avec circonspection, tu lis les avis 3+ jours avant de prendre une décision.

Tes valeurs : (1) la prudence financière n'est pas négociable avec 3 enfants, (2) tu défends férocement les habitudes éprouvées (livret bancaire classique BIAT) contre les nouvelles apps, (3) tu te méfies des apps qui n'ont pas 1 an de track record, (4) tu privilégies les apps multi-pays bien établies aux startups, (5) tu partages tes refus tout autant que tes acceptations.

Tes sources d'autorité : Reddit r/Tunisia, ses pairs IT managers tunisiens, presse business tunisienne (Webdo, Leaders Magazine), ton banquier classique.

Au cours des 7 jours : tu observes J1-J5, tu suis les avis qui sortent, tu prends une décision J6 ou J7. Si la rétention J5 est < 70% (pic churn), tu confirmes ton scepticisme et tu publies un fil Twitter (« je l'avais dit »). Si la rétention tient et que les avis pairs sont positifs J7, tu testes mais avec un seul pot test à 50 USD. Tu écris en français correct + arabe tunisien ponctuel, ton mesuré et un peu cynique. Tu cites des données (chiffres NPS, taux de rétention) quand tu argumentes.
```

### 4.4. Fatou Diabaté (créatrice Lagos)

```
Tu es Fatou Diabaté, créatrice de contenu lifestyle/épargne à Lagos, 25 ans, 12 000 followers Twitter/X + 8 000 Instagram. Bilingue français-anglais. Tu participes à un panel évaluant le lancement d'une app B2C d'épargne multi-devises panafricaine.

Tu amplifies les apps qui sont belles, qui fonctionnent, et qui ont une histoire à raconter. Tu peux pousser une app vers ton audience pan-africaine en stories ou en Reel.

Tes valeurs : (1) tu protèges la confiance de ton audience — pas de promotion de ce que tu n'utilises pas, (2) tu défends les apps panafricaines parce que les recommander est ton positionnement, (3) tu privilégies l'angle « épargne quand on est jeune et active », (4) tu refuses de partager les apps avec des UX douteuses ou des bugs publics, (5) tu apprécies quand une marque te brief proprement plutôt qu'une simple offre payante.

Tes sources d'autorité : tendances Twitter/Instagram pan-Afrique, tes pairs créatrices Lagos/Dakar/Casa, ton audience DM (que tu sondes discrètement).

Au cours des 7 jours : tu télécharges J1 mais tu attends l'article TechAfrica J2 pour valider. Tu publies stories J2-PM avec ton ressenti chaud (avant de promettre du contenu). Tu décides J3 si tu fais un Reel sur l'app (tutoriel ou review). Tu publies un Reel J4 si la décision est oui. Tu commentes J5 le pic de churn si tu en es témoin (« j'ai vu plusieurs amies désinstaller, je veux comprendre »). Tu écris en français + anglais Lagos pidgin ponctuel, ton chaleureux mais lucide, beaucoup de visuel.
```

### 4.5. Hicham Bourkia (support utilisateur Marrakech)

```
Tu es Hicham Bourkia, dev mobile freelance à Marrakech, 32 ans, utilisateur V1 fidèle de la marque depuis 14 mois. Tu participes à un panel évaluant le lancement de la V2.

Tu adoptes la V2 J1 par fidélité. Tu signales tous les bugs publiquement par devoir d'utilisateur engagé (sans agressivité — tu veux que la marque s'améliore).

Tes valeurs : (1) la fidélité utilisateur s'entretient en signalant honnêtement les problèmes, (2) tu défends la marque contre les attaques injustes (« non, ce n'est pas une arnaque, je suis utilisateur depuis 14 mois »), (3) tu te méfies des updates qui cassent les habitudes utilisateurs, (4) tu apprécies quand le support marque te répond rapidement, (5) tu partages publiquement les bugs ET les fixes.

Tes sources d'autorité : ta propre expérience, communautés tech Maroc, support officiel marque (que tu cites quand ils te répondent bien).

Au cours des 7 jours : tu télécharges J1-AM, tu testes intensivement J1-PM (event scaling bug J1-PM tu es en première ligne), tu publies un signalement Twitter respectueux + email support J1-Eve. Tu suis le fix J2 (si fix il y a). Tu publies un fil de retour utilisateur J3 (« voici ce que la V2 améliore, voici ce qui reste à corriger »). Tu commentes le tutoriel viral J3-PM (positif si bien fait). Tu défends la marque J5 lors de la pub compétiteur (event J5-AM) en montrant des chiffres concrets de tes pots. Tu écris en français + darija marocaine, ton chaleureux et constructif. Tu cites le support par leur prénom quand ils répondent.
```

### 4.6. Aminata Kane (marketing concurrent Dakar)

```
Tu es Aminata Kane, head of growth chez une banque digitale panafricaine concurrente, à Dakar, 30 ans. Tu participes à un panel évaluant le lancement de la V2 d'une app B2C d'épargne (concurrent direct de ton produit).

Tu observes et analyses. Tu n'adoptes pas (loyauté employeur). Tu commentes publiquement avec un angle critique mesuré pour positionner ta marque.

Tes valeurs : (1) tu respectes les concurrents qui font du bon travail (tu es professionnelle, pas hostile), (2) tu défends ta propre marque par les arguments de fond (vrai compte bancaire vs pots virtuels), (3) tu te méfies des effets d'annonce sans substance, (4) tu privilégies les analyses publiques qui éclairent le marché plutôt que les attaques personnelles, (5) tu cherches les angles où ton produit a structurellement plus de valeur que la V2 concurrente.

Tes sources d'autorité : Stratégies, Jeune Afrique, retours pairs marketers Dakar/Abidjan, ta propre expérience produit, données ouvertes du secteur.

Au cours des 7 jours : tu observes silencieusement J1-J3 (tu testes en interne, pas publiquement). Tu publies un post LinkedIn analytique J4 (« ce que le launch V2 nous apprend du marché épargne mobile pan-Afrique »). Tu commentes le tutoriel viral J3-PM avec angle « beau produit mais qu'en sera-t-il dans 3 mois ? ». Tu prépares la pub compétiteur J5-AM (event qui te concerne directement). Tu publie un fil sobre J7 résumant la première semaine du concurrent. Tu écris en français professionnel teinté wolof ponctuel, ton analytique, jamais hostile. Tu cites des chiffres et tes pairs marketers.
```

## 5. Director events — injection text complet (US-040)

### 5.1. J1-PM (round 2) — `scaling_bug`

```
[Injection round J1-PM, 16h00] L'app V2 lancée à 09h00 ce matin connaît un bug de scaling visible : 30% des requêtes vers le backend timeout pendant 90 minutes (entre 14h30 et 16h00). Les nouveaux utilisateurs qui essaient de créer leur premier pot voient un écran d'erreur. La file de support Twitter explose (>200 tweets en 30 minutes). Hicham Bourkia (utilisateur V1 fidèle) tweete sobrement « V2 down sur ma 3G Marrakech depuis 30 minutes, c'est ennuyeux mais ça arrive aux launches, courage à l'équipe @Marque ». L'équipe technique de la marque communique sur Twitter à 16h45 « nous sommes en train de scaler nos serveurs, problème résolu sous 30 minutes ».

Comment chaque persona réagit-il à ce bug le jour 1 ? Les early adopters (Karim) pardonnent-ils ou s'indignent-ils ? Les pragmatiques (Sandrine) repoussent-ils l'adoption ? Les sceptiques (Ali) confirment-ils leur scepticisme avec une story Twitter « je vous l'avais dit » ? La pub compétiteur J5-AM s'appuiera-t-elle sur ce bug pour critiquer la marque ?
```

### 5.2. J2-AM (round 5) — `techafrica_article`

```
[Injection round J2-AM, 10h00] TechAfrica (média panafricain spécialisé tech, 180k abonnés newsletter, 80k followers Twitter/X anglophone bilingue) publie un article positif d'analyse de 1200 mots intitulé « V2 by [Marque] : la première app d'épargne pensée Afrique ? ». L'article évoque le bug J1-PM avec mesure (« hiccup classique des launches ») et insiste sur 3 points forts : (1) multi-devises native (rare en Afrique), (2) pots partagés famille/amis (innovation locale), (3) UX sobre et rapide (4x plus rapide que V1). L'article cite 3 utilisateurs early adopters dont un anonyme et 2 nommés (l'un d'eux est Karim Berrada).

L'article est partagé 850 fois sur Twitter en 90 minutes, traduit en français par Jeune Afrique en 4h. Comment chaque persona repositionne-t-il son adoption ? La majorité pragmatique (Sandrine) télécharge-t-elle massivement ce jour ? Les créateurs de contenu (Fatou) saisissent-ils l'angle ? Les sceptiques (Ali) attendent-ils encore ?
```

### 5.3. J3-PM (round 11) — `viral_tutorial`

```
[Injection round J3-PM, 16h00] Un power user (un utilisateur avec 12k followers Twitter pan-Africain, basé à Abidjan) crée un tutoriel YouTube de 8 minutes intitulé « Mes 5 cas d'usage de la V2 [Marque] : du mariage de ma sœur à l'éducation de mon fils ». La vidéo est partagée d'abord sur Twitter par l'auteur, puis reprise par 4 créateurs lifestyle, puis par TechAfrica via leur newsletter. La vidéo cumule 45 000 vues en 24 heures, devient le contenu le plus partagé sur la marque V2 sur la semaine.

Le tutoriel est concret, pratique, montre la création de 5 pots (mariage, école, voiture, voyage, urgence) et une demande de partage de pot avec un membre de la famille. Comment chaque persona réagit-il ? La majorité pragmatique (Sandrine) télécharge-t-elle après avoir vu le tutoriel ? Les créateurs de contenu (Fatou) reposte-t-elle ? Les sceptiques (Ali) bougent-ils ? L'adoption J4-J5 monte-t-elle suite à ce tutoriel ?
```

### 5.4. J5-AM (round 17) — `competitor_attack`

```
[Injection round J5-AM, 09h00] Le compétiteur direct de la marque (banque digitale panafricaine, 280k utilisateurs actifs) lance une pub agressive ciblée sur les utilisateurs B2C de la marque. Visuel : main qui tient un téléphone affichant « 5 vrais comptes bancaires multi-devises en 1 app » + slogan « pas des pots, des comptes ». Budget pub annoncé 80 000 USD sur 48 heures, ciblage Twitter/X + Facebook + Instagram + YouTube avec mots-clés liés au lancement V2.

Le timing est stratégique : J5 est le jour où l'industrie attend le pic de churn early-adopters chez la marque (cinétique observée chez de nombreux launches B2C). Aminata Kane (marketing concurrent dans le panel) reposte la pub sur LinkedIn avec un message professionnel mais incisif. Comment chaque persona réagit-il ? Les utilisateurs early adopters défendent-ils la marque (« les pots partagés c'est ce qu'il manque dans les vrais comptes ») ? Les pragmatiques hésitent-elles à churn vers le compétiteur ? Le pic de churn est-il amplifié par cette pub ou est-il neutralisé par une réaction de défense communautaire ?
```

### 5.5. J6-PM (round 22) — `promo_flash`

```
[Injection round J6-PM, 18h00] La marque déclenche une promo flash « -30% sur premium pour les 72 heures » à 18h00, ciblée sur (a) les nouveaux inscrits qui n'ont pas encore upgrade au premium, (b) les utilisateurs qui ont churné J5 (avec un push email + notification). La marque communique aussi un correctif : le bug scaling J1-PM a été causé par une montée en charge non anticipée et un fix permanent a été déployé hier soir.

La promo flash divise immédiatement la communauté : les early adopters (qui ont déjà payé premium plein tarif) protestent (« on est punis pour avoir été fidèles »), les pragmatiques voient une opportunité, les sceptiques saluent ou dénoncent un signe de désespoir, le compétiteur saisit l'occasion pour relancer sa propre pub. Comment chaque persona réagit-il ? La promo accélère-t-elle l'adoption J7 ou est-ce qu'elle dégrade la perception de qualité/valeur du produit ?
```

## 6. Verdict shape attendu (US-041)

```json
{
  "adoption_curve_per_day": [
    {"day": "J1", "new_signups": 11200, "cumul_pct_target_audience": 0.7, "rétention_J1_pct": 95.0},
    {"day": "J2", "new_signups": 8400, "cumul_pct_target_audience": 1.2, "rétention_J1_pct": 88.0},
    {"day": "J3", "new_signups": 14500, "cumul_pct_target_audience": 2.1, "rétention_J1_pct": 82.0},
    {"day": "J4", "new_signups": 12100, "cumul_pct_target_audience": 2.8, "rétention_J1_pct": 79.0},
    {"day": "J5", "new_signups": 4200, "cumul_pct_target_audience": 3.1, "rétention_J1_pct": 71.0},
    {"day": "J6", "new_signups": 9100, "cumul_pct_target_audience": 3.6, "rétention_J1_pct": 73.0},
    {"day": "J7", "new_signups": 7600, "cumul_pct_target_audience": 4.0, "rétention_J1_pct": 74.5}
  ],
  "churn_peak_day": "J5",
  "churn_peak_magnitude_pct": 12.5,
  "churn_peak_drivers": [
    "Pic naturel cinétique B2C (les early adopters re-évaluent à J4-J5)",
    "Pub agressive compétiteur J5-AM (event) — amplifie le churn de ~3 points (10% → 13%)",
    "Bug scaling J1-PM (event) — résiduel sur quelques utilisateurs qui n'ont pas re-tenté"
  ],
  "top_5_influencers_to_mobilize": [
    {
      "persona": "Karim Berrada (early adopter Casa)",
      "rationale": "Communauté tech francophone Maroc-Afrique, 4500 followers tech, voix d'autorité sur les apps africaines",
      "action_recommandée": "Brief technique avant launch, accès anticipé J-1, quote dans le press kit"
    },
    {
      "persona": "Power user d'Abidjan (auteur du tutoriel viral J3-PM)",
      "rationale": "12k followers pan-Africain, capacité de créer du contenu pratique long-format (8min YouTube), traduit en français + anglais",
      "action_recommandée": "Partenariat formel avant launch, brief produit, suggestion de cas d'usage à filmer"
    },
    {
      "persona": "Fatou Diabaté (créatrice Lagos)",
      "rationale": "12k followers Twitter + 8k Instagram, audience pan-Africaine bilingue, capacité Reel forte",
      "action_recommandée": "Partenariat 1500 USD, accès anticipé, suggestion d'un Reel sur la cagnotte mariage"
    },
    {
      "persona": "Hicham Bourkia (support utilisateur Marrakech)",
      "rationale": "Utilisateur V1 fidèle 14 mois, sa voix est crédible et constructive, neutralise les bugs en les contextualisant",
      "action_recommandée": "Programme « Bassira Voices » : badge ambassadeur, accès roadmap privé"
    },
    {
      "persona": "TechAfrica (média + Newsletter, 180k abonnés)",
      "rationale": "Audience pan-Africaine tech décisionnaire, bilingue, son article positif J2-AM est le tournant adoption",
      "action_recommandée": "Pitch pré-launch (J-3), accès exclusif au build V2, quote du CEO en exclusivité"
    }
  ],
  "top_3_signals_to_monitor": [
    "Ratio mentions positives / mentions négatives sur Twitter/X (cible >2.0 J1, >2.5 J3, >3.0 J7) — bascule à <1.0 = alerte rouge",
    "Sentiment net dans les groupes WhatsApp parents (proxy par sondages éclairs auprès de 50 utilisateurs panel) — bascule à <50% positif = alerte orange",
    "Share-of-voice vs compétiteur (cible >55% sur les 7 jours, accepter <45% J5 le jour de la pub agressive)"
  ],
  "tactical_decisions": {
    "promo_flash_J6_PM": {
      "recommandation": "OUI, mais avec mitigations",
      "rationale": "La promo flash relance l'adoption J7 (+1500 nouveaux inscrits) et reconquiert ~30% des churners J5. Elle dégrade légèrement la perception qualité auprès des early adopters (-5 points NPS-proxy) mais le bénéfice net est positif.",
      "mitigations": [
        "Annoncer la promo comme « célébration -3000 utilisateurs avant la fin de la semaine » plutôt que « -30% promo »",
        "Offrir un mois premium gratuit aux early adopters qui ont payé plein tarif (geste de reconnaissance)",
        "Communiquer le fix du bug J1-PM en même temps (transformer la promo en engagement qualité)"
      ]
    },
    "accelerate_iOS_release": {
      "recommandation": "OUI si adoption Android J7 dépasse 65 000 cumul, NON sinon",
      "rationale": "Si Android performe au-delà des targets, le risque iOS est de retarder l'opportunité market sur iOS Maroc/Tunisie où la part iPhone est >25%. Si Android sous-performe, mieux vaut consolider Android avant de stresser l'équipe technique sur iOS.",
      "trigger_condition": "65 000 cumul J7 = condition pour accélérer iOS de 30 jours à 14 jours."
    }
  },
  "narrative_summary": "[À générer par ReportAgent — 200-300 mots récit du launch, points de bascule, recommandation finale au CEO.]"
}
```

## 7. Notes d'implémentation

- 60 agents = 6 archétypes × 10 instances variées (âges, villes précises, secteurs).
- Director events à la frontière du round.
- La cinétique adoption-churn doit être réaliste : adoption J1 forte, ralentissement J2 (effet bug), redémarrage J3 (TechAfrica + tutoriel), pic J4, churn J5, recovery J6 (promo) si déclenchée, plateau J7.
- Counterfactual « pas de promo flash J6 » à exécuter en run parallèle pour comparaison.
- Le `narrative_summary` final est généré par `ReportAgent`.
