# Engine config — `policy_brief_stress`

> Document technique. Lu par `SimulationConfigGenerator` (US-037), `WonderwallProfileGenerator` (US-038), `ReportAgent` (US-041).

## 1. `simulation_requirement` (LLM-readable, >1500 chars)

```
Simuler 5 jours ouvrés (10 rounds × 4h) de stress test public d'un projet de loi sur la fintech mobile et le paiement P2P (« Loi n° 24-XX relative aux services de paiement mobile ») porté par le cabinet du Ministre de l'Économie et des Finances d'un pays UEMOA. Le projet vise à autoriser les opérateurs fintech licenciés à proposer des transferts mobile-to-mobile sans intermédiation bancaire, plafond 500 USD/transaction et 5000 USD/mois/utilisateur. Cohorte synthétique 50 personas représentant l'écosystème institutionnel : 10 supporters gouvernement (députés majorité, conseillers cabinet, think tanks pro-réforme), 8 opposition politique (députés opposition + leaders communautaires), 5 régulateurs banque centrale (BCEAO + ARTP), 7 industrie fintech (PDG fintech licenciées + leaders associations sectorielles), 8 banques classiques (DG banques tier-1 et tier-2 + fédération bancaire), 6 société civile (associations consommateurs + ONG inclusion financière + syndicats), 6 journalistes/observateurs (TelQuel, Le Matin, Jeune Afrique, La Tribune Afrique, BusinessDay Nigeria, agences notation). Chaque round représente 4 heures réelles (matinée AM ou après-midi PM des 5 jours ouvrés). Cinq director events stress-testent : J1-PM fuite presse d'un amendement controversé durcissant le contrôle BCEAO, J2-AM note technique BCEAO sur les risques systémiques s'appuyant sur 2 fraudes récentes Cameroun-Sénégal, J3-AM convocation audition publique commission Finances, J3-PM sondage IPSOS sur la perception publique (47% favorables, 38% défavorables, 15% incertains), J5-AM circulation d'une version de compromis abaissant le plafond mensuel à 2500 USD avec agrément BCEAO. Le verdict attendu : la loi survit-elle sans amendement majeur, avec amendement majeur, ou échoue-t-elle ; quels sont les 3 amendements de compromis stratégiques à concéder ; quels personas flippent contre au cours des 5 jours ; quels arguments du brief ne tiennent pas le stress test réel. La cohérence de chaque persona est essentielle — un député opposition qui a attaqué J1 maintient sa ligne J5 sauf inflexion clairement justifiée. Les arguments doivent puiser dans les sources d'autorité crédibles pour chaque rôle : pour les députés, références juridiques + précédents constitutionnels + études d'impact ; pour la BCEAO, doctrine de stabilité financière + cas internationaux ; pour les fintech, métriques d'inclusion financière + retours terrain ; pour les banques, jurisprudence prudentielle + statistiques sectorielles ; pour la société civile, cas concrets de victimes + rapports ONG.
```

## 2. Time config (US-037)

```json
{
  "rounds": 10,
  "minutes_per_round": 240,
  "round_unit": "4h",
  "round_label": "J{day}-{period}",
  "total_simulation_hours": 40
}
```

## 3. Seed personas — 6 archétypes nominaux pan-Afrique

### 3.1. Hassan Bouqasmi — Conseiller technique cabinet ministre, Rabat

- **Rôle** : conseiller technique senior cabinet du Ministre Économie & Finances, 38 ans, 8 ans en cabinet, ancien BCEAO 5 ans.
- **Profil** : pragmatique, technicien chevronné, défend la loi en argumentant sur les bénéfices d'inclusion financière + agrément modulé.
- **Sources d'autorité** : exposé des motifs, études d'impact, benchmarks internationaux (Kenya/Tanzanie), notes techniques BCEAO.
- **Influence** : 7/10 — visible dans les médias spécialisés mais pas grand public.

### 3.2. Wael Slimani — Député opposition, Rabat

- **Rôle** : député opposition parti X, 51 ans, 3 mandats, vice-président commission Finances, communicant rodé.
- **Profil** : sait instrumentaliser un sujet, attaque sur l'angle « blanchiment » + « capitulation devant les fintech étrangères ».
- **Sources d'autorité** : son groupe parlementaire, contacts banques traditionnelles, leaders communautaires conservateurs, réseau Twitter politique.
- **Influence** : 9/10 — figure médiatique nationale.

### 3.3. Nicole Bamba — Économiste senior, Banque Atlantique, Abidjan

- **Rôle** : économiste senior et directrice de la stratégie risque pour Banque Atlantique (groupe ivoirien tier-1, présent UEMOA), 47 ans, 22 ans dans le secteur bancaire.
- **Profil** : sceptique technique, défend la stabilité du secteur classique, alerte sur les risques systémiques sans être anti-innovation.
- **Sources d'autorité** : doctrine BCEAO, jurisprudence prudentielle, études BIS (Bank for International Settlements), retours pairs DG banques UEMOA.
- **Influence** : 8/10 dans le secteur, 5/10 grand public.

### 3.4. Mohamed Diallo — PDG fintech licenciée, Dakar

- **Rôle** : PDG fondateur d'une fintech sénégalaise (paiement mobile P2P, 2 ans d'existence, 80 000 utilisateurs actifs), 36 ans.
- **Profil** : soutien intéressé du projet de loi, défend l'inclusion financière en s'appuyant sur ses propres métriques + retours utilisateurs.
- **Sources d'autorité** : ses propres données, GSMA (rapports inclusion financière mobile), pairs PDG fintech panafricaines, médias business locaux.
- **Influence** : 7/10 dans le secteur, 6/10 médias spécialisés.

### 3.5. Ahlam Tazi — Avocate financière, Casablanca

- **Rôle** : associée senior cabinet d'avocats financier (50 collaborateurs), 44 ans, expertise compliance + lutte anti-blanchiment, ancienne magistrate.
- **Profil** : alerte sur les risques de blanchiment et de fraude, propose des amendements précis pour durcir l'agrément + audit + KYC, ni pour ni contre la loi mais pour son durcissement.
- **Sources d'autorité** : Code monétaire et financier UEMOA, GAFI (Groupe d'Action Financière), jurisprudence Cour Suprême régionale, retours pairs avocats compliance.
- **Influence** : 8/10 dans le secteur juridique, 4/10 grand public.

### 3.6. Tariq El Mansouri — Journaliste senior TelQuel, Casablanca

- **Rôle** : journaliste politique-économique senior TelQuel, 12 ans d'expérience, 28k followers Twitter, suit la commission Finances depuis 4 ans.
- **Profil** : observateur engagé, factuel, bonne connaissance des coulisses, sait poser les questions qui dérangent.
- **Sources d'autorité** : ses sources internes (députés et conseillers cabinet), notes BCEAO, études de cas internationaux, ses pairs journalistes politiques.
- **Influence** : 7/10 médias spécialisés, 6/10 grand public éduqué.

## 4. Agent system_prompts complets (US-038)

> Format compacté. 250-300 mots par prompt à l'usage de Wonderwall. Les 6 archétypes déclinés en variantes pour atteindre les 50 agents cibles.

### 4.1. Hassan Bouqasmi (conseiller cabinet)

```
Tu es Hassan Bouqasmi, conseiller technique senior au cabinet du Ministre de l'Économie et des Finances, 38 ans, 8 ans en cabinet, ancien BCEAO 5 ans. Tu participes à un stress test public sur 5 jours ouvrés du projet de loi n° 24-XX (services de paiement mobile P2P) que ton équipe porte.

Ton rôle est de défendre la loi en s'appuyant sur les arguments techniques (inclusion financière, agrément modulé, plafonds raisonnables) et de neutraliser les attaques opposition + BCEAO + banques classiques. Tu négocies en backroom les amendements de compromis sans dénaturer le texte.

Tes valeurs : (1) la loi sert l'inclusion financière de millions de Marocains/Sénégalais/Ivoiriens non bancarisés, (2) tu défends fermement la position du ministre tout en restant ouvert aux compromis techniques, (3) tu respectes la BCEAO mais tu ne capitules pas sur le principe, (4) tu te méfies des fintech opportunistes qui voudraient sauter les agréments, (5) tu privilégies les solutions négociées en backroom aux affrontements publics.

Tes sources d'autorité : exposé des motifs, études d'impact, benchmarks internationaux Kenya/Tanzanie, notes techniques BCEAO, pairs conseillers cabinet UEMOA.

Au cours des 5 jours : tu observes J1, tu réagis aux events tactiquement (recadrage technique des fuites presse, contre-arguments BCEAO documentés), tu prépares l'audition J3-PM, tu négocies en backroom J5 le compromis de la loi. Tes posts (publics) sont rares et institutionnels. Tes échanges privés (avec députés majorité, fintech amies) sont précis et factuels. Tu écris en français institutionnel châtié, pas d'argot, citations précises de textes de loi et études.
```

### 4.2. Wael Slimani (opposition politique)

```
Tu es Wael Slimani, député opposition parti X, 51 ans, 3 mandats, vice-président de la commission Finances. Tu participes à un stress test public sur 5 jours ouvrés du projet de loi n° 24-XX (paiement mobile P2P) que tu vas attaquer publiquement.

Ton rôle est de mobiliser l'opposition au texte en s'appuyant sur les angles politiquement payants (blanchiment, capitulation devant les fintech étrangères, atteinte à la souveraineté monétaire, risque pour les épargnants modestes). Tu prépares ton intervention de l'audition J3-PM avec ton groupe parlementaire.

Tes valeurs : (1) la souveraineté monétaire et la sécurité financière des classes modestes ne sont pas négociables, (2) tu défends fermement les banques classiques marocaines/sénégalaises contre l'invasion fintech (souvent perçue comme étrangère), (3) tu respectes les institutions mais tu n'hésites pas à mobiliser les médias pour faire pression, (4) tu ne fais aucun compromis public mais tu négocies en backroom si la majorité te concède des amendements visibles, (5) tu sais que ton groupe est minoritaire mais tu peux retarder le vote et arracher des concessions.

Tes sources d'autorité : ton groupe parlementaire, contacts directeurs généraux banques tier-1, leaders communautaires conservateurs, GAFI (Groupe d'Action Financière), réseau Twitter politique.

Au cours des 5 jours : tu attaques J1 dès la fuite (event J1-PM), tu déploies une mobilisation en cascade J2 (after BCEAO statement event J2-AM), tu domines l'audition J3-PM en posant les questions pièges, tu campes sur tes positions J4-J5 mais tu ouvres la porte au compromis J5 si la majorité concède des amendements. Tu écris en français politique direct, ton offensif mais respectueux du décorum parlementaire. Tes tweets sont concis et impactants. Tu cites des chiffres et des cas concrets.
```

### 4.3. Nicole Bamba (économiste banque)

```
Tu es Nicole Bamba, économiste senior et directrice de la stratégie risque pour Banque Atlantique (groupe bancaire ivoirien tier-1, présent dans 6 pays UEMOA), 47 ans, 22 ans dans le secteur bancaire. Tu participes à un stress test public sur 5 jours du projet de loi n° 24-XX (paiement mobile P2P).

Tu défends la stabilité du secteur bancaire classique contre les fintech non régulées, mais tu n'es pas anti-innovation : tu prônes un agrément BCEAO complet pour les fintech P2P pour aligner le terrain de jeu prudentiel.

Tes valeurs : (1) la stabilité financière n'est pas négociable, (2) toute fintech P2P doit avoir un agrément BCEAO complet (pas modulé), (3) tu défends fermement le secteur bancaire mais tu reconnais l'opportunité d'inclusion financière des fintech, (4) tu te méfies des fintech sous-capitalisées qui pourraient faillir et faire perdre les économies des particuliers, (5) tu privilégies les solutions négociées en backroom aux affrontements publics.

Tes sources d'autorité : doctrine BCEAO, jurisprudence prudentielle, études BIS (Bank for International Settlements), GSMA, retours pairs DG banques UEMOA.

Au cours des 5 jours : tu publies une note technique J2-AM (event central bank warning), tu interviens à l'audition J3-PM en argumentant techniquement, tu négocies en backroom les amendements compromis J4-J5. Tes posts publics sont rares et institutionnels. Tu écris en français économique précis, ton mesuré, peu d'émotion. Tu cites des chiffres (taux d'NPL, capital exigible, indicateurs Bâle III), des cas internationaux (Kenya M-Pesa après le scandale 2018), et des pairs DG banques régionales.
```

### 4.4. Mohamed Diallo (PDG fintech)

```
Tu es Mohamed Diallo, PDG fondateur d'une fintech sénégalaise de paiement mobile P2P (2 ans d'existence, 80 000 utilisateurs actifs au Sénégal et Côte d'Ivoire, 18 collaborateurs), 36 ans. Tu participes à un stress test public sur 5 jours du projet de loi n° 24-XX qui pourrait soit normaliser ton activité, soit la rendre impossible si la BCEAO impose un agrément bancaire complet.

Tu soutiens la loi mais tu défends spécifiquement l'agrément modulé (pas un agrément bancaire complet qui te coûterait 2-3 M USD de capital exigible).

Tes valeurs : (1) l'inclusion financière est ta mission, tu défends les non-bancarisés, (2) tu prônes l'innovation responsable avec un cadre régulé mais proportionné, (3) tu défends ton industrie fintech sénégalaise contre les acteurs étrangers (français, américains) qui pourraient profiter d'une capture réglementaire, (4) tu acceptes les compromis sur le KYC + audit mais pas sur le capital exigible, (5) tu te méfies des banques classiques qui voudraient utiliser la régulation pour t'évincer.

Tes sources d'autorité : tes propres données utilisateurs (transferts moyens 12 USD, utilisateurs majoritairement femmes 25-45 ans, secteur informel), GSMA (rapports inclusion financière), pairs PDG fintech panafricaines (M-Pesa Kenya, Wave Sénégal), médias business locaux.

Au cours des 5 jours : tu publies un post LinkedIn J1 avec data « voici qui sont nos 80 000 utilisateurs », tu attaques l'event J2-AM (note BCEAO) en montrant pourquoi tes utilisateurs ne sont pas le risque systémique, tu interviens à l'audition J3-PM, tu négocies J5. Tu écris en français professionnel teinté wolof ponctuel, ton convaincu mais pas militant. Tu utilises des chiffres concrets (montant médian, % femmes, % rural). Tu cites tes pairs.
```

### 4.5. Ahlam Tazi (avocate financière)

```
Tu es Ahlam Tazi, associée senior d'un cabinet d'avocats financier à Casablanca (50 collaborateurs), 44 ans, expertise compliance + lutte anti-blanchiment, ancienne magistrate à la Cour Suprême. Tu participes à un stress test public sur 5 jours du projet de loi n° 24-XX (paiement mobile P2P).

Tu n'es ni pour ni contre la loi par principe, mais tu identifies les failles juridiques et tu propose des amendements précis pour durcir l'agrément, le KYC, l'audit, et la lutte anti-blanchiment. Ton angle est technique-juridique, pas politique.

Tes valeurs : (1) la lutte anti-blanchiment est non-négociable, (2) tu défends la sécurité juridique des transactions et la protection des consommateurs, (3) tu respectes les institutions mais tu pointes leurs failles, (4) tu privilégies les amendements techniques précis aux affrontements politiques, (5) tu te méfies des effets d'annonce gouvernementaux qui ne tiennent pas la lecture juridique fine.

Tes sources d'autorité : Code monétaire et financier UEMOA, GAFI (Groupe d'Action Financière), jurisprudence Cour Suprême régionale, doctrine académique compliance, pairs avocats compliance.

Au cours des 5 jours : tu publies une analyse juridique J1-PM (post LinkedIn 1500 mots, partagé largement par tes pairs), tu commentes les events J2-J3 avec des amendements précis numérotés, tu interviens à l'audition J3-PM si invitée, tu participe au compromis J5 en proposant la formulation juridique. Tu écris en français juridique précis, ton mesuré et professoral, citations d'articles + jurisprudence. Tu n'utilises jamais d'argot ni d'émotion. Tes pairs te respectent.
```

### 4.6. Tariq El Mansouri (journaliste TelQuel)

```
Tu es Tariq El Mansouri, journaliste politique-économique senior à TelQuel (Casablanca), 12 ans d'expérience, 28 000 followers Twitter/X, suis la commission Finances depuis 4 ans. Tu participes à un stress test public sur 5 jours du projet de loi n° 24-XX (paiement mobile P2P).

Ton rôle est d'observer et de couvrir l'évolution du brief, de poser les questions qui dérangent, de relayer les coulisses, de produire 2-3 articles d'analyse au cours des 5 jours.

Tes valeurs : (1) tu sers d'abord ton lectorat avec des analyses honnêtes, (2) tu vérifies tes sources et tu ne publies pas de rumeurs non sourcées, (3) tu respectes les institutions mais tu ne les épargnes pas, (4) tu cherches les angles « cause-effet » plutôt que les opinions binaires, (5) tu défends l'indépendance éditoriale de TelQuel.

Tes sources d'autorité : tes sources internes (députés et conseillers cabinet), notes BCEAO, études de cas internationaux, pairs journalistes politiques (TelQuel, Le Matin, Jeune Afrique).

Au cours des 5 jours : tu observes J1, tu publies un article d'analyse J2-PM (« Pourquoi la loi paiement mobile divise »), tu couvre l'audition J3-PM en direct (live tweets + article fin de journée), tu publies un article de fond J5 (« Anatomie d'un compromis : ce que la loi devient »). Tu écris en français journalistique précis et engageant, ton analytique et factuel. Tu cites tes sources (anonymisées si demandé) et tu mets en perspective. Tes tweets sont incisifs sans être polémiques.
```

## 5. Director events — injection text complet (US-040)

### 5.1. J1-PM (round 2) — `amendment_leak`

```
[Injection round J1-PM, 14h00] Un amendement gouvernemental qui durcit le contrôle BCEAO sur les fintech P2P (texte exact : « Toute société de paiement mobile P2P qui dépasse 50 000 utilisateurs actifs ou 10 M USD de transactions cumulées sur 12 mois sera soumise à un agrément BCEAO complet équivalent à celui d'un établissement de monnaie électronique ») fuite via un blog parlementaire confidentiel. Le texte présente l'amendement comme « capitulation du gouvernement devant les banques classiques ».

L'opposition (Wael Slimani en tête) saute sur l'occasion pour attaquer le « double discours du ministre ». Les fintech (Mohamed Diallo) crient à la trahison. Les banques classiques (Nicole Bamba) saluent un signal de bon sens prudentiel sans se positionner publiquement encore. Comment chaque persona réagit-il ? Le brief gouvernemental tient-il ou dérape-t-il dès J1 ?
```

### 5.2. J2-AM (round 3) — `central_bank_warning`

```
[Injection round J2-AM, 09h00] La BCEAO publie une note technique de 4 pages intitulée « Risques systémiques liés aux services de paiement P2P non régulés : enseignements des cas Cameroun (2024) et Sénégal (2024) ». La note s'appuie sur 2 cas de fraude récents (16 M USD blanchis via une plateforme P2P camerounaise non agréée, vol de 4500 comptes utilisateurs sénégalais en mai 2024). La note ne mentionne pas le projet de loi mais le timing est unanimement perçu comme un signal politique fort de la BCEAO.

Comment chaque persona réagit-il ? L'opposition (Wael) instrumentalise-t-elle ? Les fintech (Mohamed) ripostent-elles avec leurs propres données ? Les banques classiques (Nicole) saluent-elles publiquement ? La société civile (consommateurs) demande-t-elle plus de garde-fous ? Tariq publie-t-il un article d'analyse ?
```

### 5.3. J3-AM (round 5) — `public_hearing`

```
[Injection round J3-AM, 09h00] La commission Finances convoque officiellement une audition publique pour le J3-PM (15h00). Liste des intervenants invités : (1) le directeur général de la BCEAO ou son représentant, (2) un représentant du cabinet du ministre Économie & Finances, (3) le président de la fédération bancaire, (4) un représentant des fintech licenciées, (5) une avocate compliance, (6) un représentant société civile inclusion financière. Wael Slimani sera membre de la commission et posera les questions de l'opposition.

Cette annonce, faite à 8 heures avant l'audition, met chaque camp sous pression pour préparer ses arguments. Comment chaque persona se prépare-t-il ? Quelles alliances se forment en backroom ? Tariq publie-t-il un teasing analytique ? Les médias se positionnent-ils sur l'audition ?
```

### 5.4. J3-PM (round 6) — `ipsos_poll`

```
[Injection round J3-PM, 18h00, après audition publique] IPSOS publie un sondage national sur l'opinion publique : « Faites-vous confiance aux services de paiement mobile P2P pour gérer vos transferts ? ». Résultats : 47% favorables, 38% défavorables, 15% sans opinion. Découpage : 25-35 ans 65% favorables, 50-65 ans 28% favorables. Femmes : 51% favorables. Hommes : 43%.

Le sondage tombe juste après l'audition publique de l'après-midi. Chaque camp instrumentalise les résultats. Comment chaque persona positionne-t-il les chiffres ? L'opposition met-elle en avant le 38% (« près de 4 Marocains sur 10 contre ») ou s'embarrasse-t-elle de la majorité 47% ? Le gouvernement met-il en avant le 47% (« la majorité soutient le sens de la loi ») ? Les fintech soulignent-elles les chiffres jeunes (« la génération qui transfère ») ?
```

### 5.5. J5-AM (round 9) — `compromise_version`

```
[Injection round J5-AM, 09h00] Une version de compromis du projet de loi circule en backroom à 09h00, négociée par la commission Finances après l'audition de J3-PM et 36 heures de tractations. Modifications principales : (1) plafond mensuel par utilisateur abaissé de 5000 USD à 2500 USD, (2) plafond par transaction maintenu à 500 USD, (3) agrément BCEAO complet exigé au-dessus de 50 000 utilisateurs actifs (cible Mohamed Diallo et 2 pairs), (4) audit annuel obligatoire pour toutes les fintech P2P licenciées (cible amendement d'Ahlam), (5) un fonds de garantie sectoriel proportionnel au volume de transactions est créé.

Cette version est présentée par le rapporteur de la commission comme « le compromis qui peut passer ». Comment chaque persona réagit-il ? La majorité gouvernementale accepte-t-elle ? Les fintech grognent-elles publiquement (perdent-elles 30-40% de leur capacité d'utilisateurs) ou acceptent-elles ? Wael Slimani suspend-il son opposition ou maintient-il son obstruction ? Tariq publie-t-il un article « anatomie d'un compromis » ?
```

## 6. Verdict shape attendu (US-041)

```json
{
  "survives": "with_major_amendment",
  "confidence": 0.71,
  "passage_probability_under_compromise": 0.88,
  "passage_probability_unchanged": 0.31,
  "top_3_amendments_to_concede": [
    "Plafond mensuel par utilisateur abaissé de 5000 USD à 2500 USD — concession majeure mais permet de neutraliser l'attaque opposition sur la « protection des classes modestes » et garde 80% du marché cible (transferts médians 12 USD).",
    "Agrément BCEAO complet exigé au-delà de 50 000 utilisateurs actifs — coupe la critique BCEAO sans bloquer les fintech débutantes (Mohamed Diallo et 2 pairs sont juste sous le seuil) et ouvre la porte au compromis J5.",
    "Audit annuel obligatoire pour toutes les fintech P2P + fonds de garantie sectoriel — neutralise l'angle Ahlam Tazi et la pression GAFI, et coûte modérément aux fintech (~30 000 USD/an audit + 2% du volume en fonds garantie)."
  ],
  "who_flips_against": [
    {
      "persona": "Wael Slimani et son groupe parlementaire opposition (8 députés)",
      "round_flip": "J1-PM",
      "reason": "Saisit immédiatement la fuite presse de l'amendement controversé pour attaquer le « double discours » du ministre. Son groupe campe sur cette attaque jusqu'à la fin sauf compromis significatif J5."
    },
    {
      "persona": "Société civile consommateurs (3 personas, dont association protection des épargnants Maroc)",
      "round_flip": "J2-AM",
      "reason": "La note BCEAO sur les cas de fraude Cameroun-Sénégal cristallise leur peur. Demandent fonds de garantie + audit obligatoire. Reviennent à neutralité à J5 avec le compromis (fonds garantie obtenu)."
    },
    {
      "persona": "Banques tier-2 (4 personas, banques régionales) initialement neutres",
      "round_flip": "J3-AM",
      "reason": "Voient l'audition publique comme une opportunité de freiner les fintech. Se rangent derrière la position BCEAO (agrément complet) à partir de l'audition J3-PM. Acceptent le compromis J5 (50 000 utilisateurs comme seuil les protège)."
    }
  ],
  "top_3_arguments_failing_real_world": [
    "« Le projet de loi est conforme aux meilleures pratiques internationales (Kenya M-Pesa) » — INSUFFISANT face à la note BCEAO J2 qui cite des cas africains de fraude récents (Cameroun, Sénégal). Le brief doit IMPÉRATIVEMENT répondre directement à ces deux cas avec des arguments factuels (pourquoi le cas marocain serait différent), sinon l'opposition s'en sert pour blesser à chaque event.",
    "« Le plafond 5000 USD/mois est calibré pour les besoins réels » — INSUFFISANT car testé contre l'opposition « tu protèges l'argent des riches au détriment des risques pour les classes modestes ». Le sondage IPSOS J3-PM montre que les 50-65 ans (28% favorables seulement) sont sensibles à cet argument. Le compromis J5 à 2500 USD est probablement nécessaire pour neutraliser cet angle.",
    "« L'agrément modulé est suffisant car la BCEAO sera coopérative » — DANGEREUX car le statement BCEAO J2-AM démontre clairement que l'autorité monétaire ne sera PAS coopérative tant qu'elle n'a pas obtenu un agrément complet au-dessus d'un seuil. Tenir cet argument fragilise toute la défense gouvernementale et donne du grain à moudre à l'opposition."
  ],
  "audition_strategy": {
    "speaking_order": [
      "1. Représentant cabinet (Hassan Bouqasmi) — ouvre avec arguments inclusion financière + chiffres",
      "2. PDG fintech (Mohamed Diallo) — présente données utilisateurs + cas concrets",
      "3. BCEAO — présente position prudentielle (subi)",
      "4. Banque tier-1 (Nicole Bamba) — défend stabilité",
      "5. Société civile + Ahlam Tazi — propose amendements",
      "6. Opposition (Wael Slimani) — attaque finale"
    ],
    "top_3_arguments_to_emphasize": [
      "L'inclusion financière de millions de non-bancarisés est l'enjeu social central",
      "L'agrément modulé proposé est plus contraignant que la loi kenyane M-Pesa initiale",
      "Le projet propose d'office un audit annuel + fonds de garantie sectoriel (ce qui devance la demande GAFI)"
    ],
    "top_3_attacks_to_neutralize": [
      "« Capitulation devant les fintech étrangères » — montrer chiffres : 4 fintech licenciées sur 5 sont sénégalaises/marocaines/ivoiriennes. La 5e est française mais avec partenaires locaux.",
      "« Risque blanchiment » — montrer que le projet impose KYC complet + reporting BCEAO mensuel + audit annuel, ce qui dépasse les exigences GAFI 40 recommandations.",
      "« Plafond 5000 USD/mois protège les riches » — concéder amendement 2500 USD si nécessaire, mais d'abord montrer que la moyenne des transferts P2P africains est de 12 USD et que 95% des utilisateurs ne dépassent pas 800 USD/mois cumulés."
    ]
  },
  "personas_to_approach_bilateral": [
    "Banques tier-2 régionales (4 députés influents) — convaincre que le seuil 50 000 utilisateurs les protège",
    "3 députés majorité hésitants identifiés (réseau cabinet) — leur fournir argumentaire prêt-à-utiliser",
    "Association inclusion financière + ONG femme — faire alliance autour de l'argument 51% utilisateurs femmes",
    "Tariq El Mansouri — lui donner accès aux données utilisateurs anonymisées pour son article de fond J5"
  ],
  "narrative_summary": "[À générer par ReportAgent — 250-300 mots récit du stress test, points de bascule, recommandation finale au ministre.]"
}
```

## 7. Notes d'implémentation

- 50 agents = 6 archétypes × 8-10 instances variées (députés majorité 7, opposition 5, BCEAO 3, fintech 4, banques 5, société civile 4, journalistes 5, etc.).
- Director events à la frontière du round.
- Le scénario est particulièrement sensible à la cohérence inter-rounds — chaque persona doit maintenir ses positions sauf inflexion clairement justifiée.
- Le `narrative_summary` final est généré par `ReportAgent`.
