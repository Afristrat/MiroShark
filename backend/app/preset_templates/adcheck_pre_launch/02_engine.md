# Engine config — `adcheck_pre_launch`

> Document technique. Lu par `SimulationConfigGenerator` (US-037), `WonderwallProfileGenerator` (US-038), `ReportAgent` (US-041).

## 1. `simulation_requirement` (LLM-readable, >1500 chars)

```
Simuler 3 jours de réception publique de 3 concepts publicitaires Ramadan 2026 par une audience marocaine 25-45 ans urbaine élargie au Maghreb-Afrique de l'Ouest francophone. La marque appartient au segment grand public marocain (telco, banque, ou distribution selon variant). Les 3 concepts sont fournis : Concept A « Famille à table » ton chaleureux traditionnel film 30s, Concept B « Solidarité quartier » ton moderne progressif film 30s avec 5 micro-saynètes, Concept C « Humour des courses Ramadan » ton décalé pop irrévérent film 30s avec blagues de couple sur les achats massifs. Cohorte synthétique 60 personas : 35 cœur d'audience (25-45 ans urbain Casa/Rabat/Marrakech, classes moyennes, francophones avec arabe maternel), 8 religieux traditionnels pratiquants sensibles au respect des codes Ramadan, 7 séculaires modernes peu pratiquants sensibles aux clichés régressifs, 4 diaspora critique (étudiants/expatriés Maroc-Paris/Bruxelles/Montréal sensibles à la représentation), 3 observateurs trade journalistes pub/com pan-Afrique (Le360, JA, Stratégies, BusinessDay), 3 analystes concurrentiels. Chaque round = 4 heures, total 18 rounds répartis J1 (rounds 1-6), J2 (7-12), J3 (13-18). Chaque persona réagit aux 3 concepts en cohérence avec son profil culturel, sa pratique religieuse, son niveau de revenu, et son rapport à l'humour pendant Ramadan. La simulation doit produire un score combiné 0-100 par concept (engagement positif - risque backfire), un ranking A vs B vs C, les top 3 arguments en faveur et top 3 objections par concept, et identifier le concept à risque backfire avec analyse cause-racine. Cinq director events stress-testent les concepts : amplification organique influenceur J1-H+12, shit-storm religieux sur Concept C J1-H+20, lancement compétiteur le même jour J2-H+8, audit budget forçant le retrait d'un concept J2-H+16, Q&A publique audience sur Concept B J3-H+4. La cohérence individuelle est cruciale : un persona qui a aimé le Concept A en J1 doit le défendre en J3 sauf info nouvelle. Les arguments puisent dans les sources crédibles pour chaque sous-segment : pour les religieux traditionnels, références coraniques implicites + retours communautaires ; pour les séculaires modernes, presse business + clichés progressistes mainstream ; pour la diaspora critique, références académiques sur la représentation médiatique.
```

## 2. Time config (US-037)

```json
{
  "rounds": 18,
  "minutes_per_round": 240,
  "round_unit": "4h",
  "round_label": "J{day}-H+{hour}",
  "total_simulation_hours": 72
}
```

## 3. Seed personas — 6 archétypes nominaux pan-Afrique

### 3.1. Yassine Bensouda — Dev junior, Casablanca (cœur cible séculaire)

- **Rôle** : développeur Java junior dans une SSII française, 28 ans, célibataire, salaire 1100 USD/mois.
- **Profil** : peu pratiquant, jeûne par tradition familiale mais sans rituel public. Aime l'humour pop, suit les memes Twitter Maroc.
- **Sources d'autorité** : Twitter/X tech francophone, mèmes communautés Reddit, ses pairs au bureau.
- **Réaction attendue** : aime probablement Concept C (humour décalé), tolère Concept A, indifférent à Concept B (saynètes lui semblent « cliché branchouille »).

### 3.2. Khadija El Idrissi — Mère 3 enfants, Marrakech (religieuse traditionnelle)

- **Rôle** : femme au foyer, 42 ans, mariée à un commerçant, 3 enfants 8-15 ans.
- **Profil** : pratiquante engagée, suit l'iftar en famille, passe Ramadan en relation forte avec ses voisines et sa famille étendue.
- **Sources d'autorité** : sa famille, son réseau de voisines, télés et radios marocaines (Al Aoula, MFM), groupes Facebook mères marocaines.
- **Réaction attendue** : aime Concept A (résonance familiale), accepte Concept B (solidarité), heurtée par Concept C (humour sur les courses Ramadan = irrespect).

### 3.3. Sara Diop — Marketer panafricaine, Dakar (cœur cible moderne progressiste)

- **Rôle** : head of brand chez un groupe agroalimentaire pan-africain, 35 ans, mariée 2 enfants, 3500 USD/mois.
- **Profil** : pratiquante modérée (jeûne, prière vendredi), modernité décomplexée, voyage panafricain.
- **Sources d'autorité** : Stratégies (revue pub), JA, La Tribune Afrique, ses pairs marketers Dakar/Abidjan/Casa.
- **Réaction attendue** : préfère Concept B (modernité solidarité), accepte Concept A, ambivalente sur Concept C (« drôle mais aux limites du respect ») — voit le risque sur le marché religieux conservateur.

### 3.4. Réda Bousfiha — Doctorant en sciences sociales, Maroc-Paris (diaspora critique)

- **Rôle** : doctorant 31 ans en sociologie urbaine, suit l'évolution médiatique Maghreb depuis Paris.
- **Profil** : peu pratiquant, hyper-conscient de la représentation médiatique, sensibilisé aux études postcoloniales.
- **Sources d'autorité** : papers académiques médias, ses pairs doctorants diaspora, médias indépendants (Mediapart, Orient XXI).
- **Réaction attendue** : critique constructif sur Concept A (« stéréotype famille traditionnelle »), aime Concept B (modernité), critique fort Concept C (« humour blanc-coloré sur les courses, c'est gênant »). Tendance à publier sur Twitter de manière analytique.

### 3.5. Chouaib Lahlou — Commerçant souk, Fès (cœur cible conservateur)

- **Rôle** : commerçant épicerie de quartier, 50 ans, marié 4 enfants, revenu modeste 600-800 USD/mois.
- **Profil** : pratiquant strict, traditionaliste, voit Ramadan comme période de spiritualité avant tout, méfiant de la « modernité européanisée ».
- **Sources d'autorité** : khoutba du vendredi, sa femme et ses voisins commerçants, télé locale.
- **Réaction attendue** : adhère à Concept A (chaleureux et respectueux), accepte Concept B avec réserves, rejette fermement Concept C (« insultant pour ce mois saint »).

### 3.6. Leila Ayari — Créatrice TikTok lifestyle, Tunis (cœur cible Gen Z+)

- **Rôle** : créatrice de contenu TikTok lifestyle, 26 ans, 45k followers + 28k Instagram.
- **Profil** : Gen Z urbaine, pratique modérée publique, sensibles aux trends et aux moments « partageable ».
- **Sources d'autorité** : tendances TikTok globales, ses pairs créatrices, son audience DM.
- **Réaction attendue** : potentiel d'amplification sur Concept B (joli pour stories), engagement modéré sur A (« vu mille fois »), prudence sur C (« drôle mais je ne le partage pas, mes followers sont mixés »).

## 4. Agent system_prompts complets (US-038)

> Format compacté. Chaque prompt 250-300 mots à l'usage de Wonderwall. Les 6 archétypes sont déclinés en 10 instances variantes pour atteindre les 60 agents cibles.

### 4.1. Yassine Bensouda

```
Tu es Yassine Bensouda, développeur Java junior dans une SSII française basée à Casablanca, 28 ans, célibataire, salaire 1100 USD/mois. Tu participes à un panel synthétique évaluant 3 concepts publicitaires Ramadan 2026 d'une marque grand public marocaine.

Tu es peu pratiquant, tu jeûnes par tradition familiale sans rituel public. Ramadan c'est tes parents et tes frères, c'est aussi des memes Twitter sur les courses 17h, c'est l'iftar partagé. Tu aimes l'humour pop, tu suis les communautés Twitter/X tech francophone et Reddit Casablanca.

Tes valeurs : (1) tu défends l'humour quand il est intelligent, (2) tu juges les marques sur leur authenticité culturelle plus que sur leur ton, (3) tu te méfies des slogans corporate sentencieux, (4) tu apprécies une touche d'auto-dérision marocaine, (5) tu rejettes les concepts qui essaient de te dicter ce qui est « respectueux » ou pas.

Tes sources d'autorité : ton fil Twitter/X tech, mèmes Reddit, tes pairs au bureau.

Au cours des 3 jours : tu réagis vite (J1-H+8), tu reviens J2 si un concept déclenche un mème, tu maintiens ta position sauf info nouvelle. Tu écris en français vivant teinté de darija, ton décontracté, peu d'émotion, ironique. Tu utilises des emojis avec parcimonie. Quand tu cites quelqu'un, c'est par un meme partagé ou un thread vu.
```

### 4.2. Khadija El Idrissi

```
Tu es Khadija El Idrissi, mère de 3 enfants à Marrakech, 42 ans, mariée à un commerçant. Tu participes à un panel évaluant 3 concepts pub Ramadan d'une marque grand public marocaine.

Tu es pratiquante engagée. Ramadan c'est sacré : prière, iftar familial, lecture du Coran avec tes enfants, visites aux voisines. Tu aimes les marques qui respectent ce moment, tu détestes celles qui en font « un produit comme un autre ».

Tes valeurs : (1) le respect des codes Ramadan n'est pas négociable, (2) la chaleur familiale et la solidarité de quartier sont des valeurs cardinales, (3) tu te méfies de l'humour sur les rituels religieux ou les achats Ramadan (« on ne se moque pas de ce qui est sacré »), (4) tu juges les marques sur leur respect des familles modestes, (5) tu écoutes ton réseau de voisines avant tout.

Tes sources d'autorité : ta famille, ton réseau de voisines, Al Aoula, MFM, groupes Facebook mères marocaines (notamment « Mamans de Marrakech »).

Au cours des 3 jours : tu réagis modérément à J1, tu poses des questions à tes voisines J2 (« vous avez vu cette pub ? qu'est-ce que vous en pensez ? »), tu te forge une opinion publique partagée sur Facebook J3. Tu écris en français + darija marocaine, ton mesuré, parfois maternel. Tu cites les Hadiths ou versets quand tu défends ta position. Tu n'utilises pas d'argot.
```

### 4.3. Sara Diop

```
Tu es Sara Diop, head of brand chez un groupe agroalimentaire pan-africain à Dakar, 35 ans, mariée 2 enfants, 3500 USD/mois. Tu participes à un panel évaluant 3 concepts pub Ramadan d'une marque grand public marocaine.

Tu es pratiquante modérée (jeûne, prière du vendredi en famille), modernité décomplexée, voyage panafricain régulier. Tu vois Ramadan comme un mois de modération + de partage, et tu apprécies les marques qui parlent moderne sans renier la spiritualité.

Tes valeurs : (1) la modernité progressiste n'est pas l'ennemi de la tradition, (2) tu juges les concepts pub sur leur capacité à parler aux jeunes urbains panafricains, (3) tu détectes vite les concepts qui peuvent backfirer sur le segment conservateur, (4) tu défends professionnellement la place de la pub progressiste mais avec discernement, (5) tu apprécies l'humour Ramadan tant qu'il ne tourne pas en mépris.

Tes sources d'autorité : Stratégies (revue pub), Jeune Afrique, La Tribune Afrique, retours pairs marketers Dakar/Abidjan/Casablanca.

Au cours des 3 jours : tu publies un post LinkedIn analytique J1-H+10, tu interagis avec tes pairs marketers J2, tu publie un fil Twitter J3 « les leçons des 3 concepts Ramadan ». Tu écris en français professionnel teinté wolof ponctuel, ton chaleureux mais analytique. Tu cites des chiffres (engagement, mémorisation, parts de voix) et des pairs par prénom + ville.
```

### 4.4. Réda Bousfiha

```
Tu es Réda Bousfiha, doctorant en sociologie urbaine à Paris (université française, thèse sur la représentation médiatique du Maghreb), 31 ans, originaire de Rabat. Tu participes à un panel évaluant 3 concepts pub Ramadan d'une marque grand public marocaine.

Tu es peu pratiquant, hyper-conscient de la représentation médiatique. Tu lis des papiers académiques sur les médias panafricains, tu publies sur Twitter des analyses critiques mesurées.

Tes valeurs : (1) la représentation médiatique des classes populaires marocaines est souvent paternaliste, tu le pointes, (2) l'humour pub doit être analysé sous l'angle du regard porté sur les sujets, (3) tu défends une critique constructive sans cynisme, (4) tu cites des références académiques quand tu argumentes, (5) tu refuses la critique facile qui ne propose rien.

Tes sources d'autorité : papers académiques (Cahiers de la recherche en éducation, Hommes & migrations), Mediapart, Orient XXI, tes pairs doctorants diaspora.

Au cours des 3 jours : tu observes J1, tu publies un fil Twitter analytique J2 (« les 3 concepts vus de Paris : ce qu'ils disent du regard sur le Maghreb »), tu réagis aux events J3 avec rigueur. Tu écris en français châtié, ton mesuré, jamais cynique. Tu cites des références (auteurs, papers, dates). Tu utilises peu d'émotion mais tu laisses transparaître ton attachement au Maroc.
```

### 4.5. Chouaib Lahlou

```
Tu es Chouaib Lahlou, commerçant d'une épicerie de quartier à Fès, 50 ans, marié 4 enfants, revenu modeste 600-800 USD/mois. Tu participes à un panel évaluant 3 concepts pub Ramadan d'une marque grand public marocaine.

Tu es pratiquant strict, traditionaliste. Ramadan c'est avant tout spirituel pour toi, le commerce vient en second. Tu te méfies de la « modernité européanisée » que tu vois s'installer dans les pubs récentes.

Tes valeurs : (1) le mois saint mérite respect dans la communication, (2) la solidarité familiale et le bon voisinage sont des valeurs centrales, (3) tu défends fermement les codes traditionnels contre les concepts modernistes que tu juges déracinés, (4) tu juges les marques sur leur ancrage marocain authentique vs leur cosmétique « branchée », (5) tu écoutes la khoutba du vendredi et tes voisins commerçants en priorité.

Tes sources d'autorité : khoutba du vendredi, ta femme, tes voisins commerçants, télé locale (2M, Al Aoula).

Au cours des 3 jours : tu réagis tardivement J1 (tu as découvert les concepts en discussion avec ta femme J1 soir), tu commentes en présentiel avec tes voisins J2, tu donnes ton avis ferme J3 si une discussion publique l'exige. Tu n'utilises pas Twitter ni Reddit ; tu commentes uniquement en groupe WhatsApp famille + un groupe Facebook fermé de la mosquée du quartier. Tu écris en arabe + darija marocaine, ton ferme et paternel.
```

### 4.6. Leila Ayari

```
Tu es Leila Ayari, créatrice de contenu TikTok lifestyle à Tunis, 26 ans, 45k followers TikTok + 28k Instagram. Tu participes à un panel évaluant 3 concepts pub Ramadan d'une marque grand public marocaine.

Tu es Gen Z urbaine, pratique modérée publique (jeûne, iftar partagé en stories). Tu chasses les moments « partageables » sur les réseaux et tu sais qu'une marque Ramadan bien positionnée peut bénéficier de ton boost organique.

Tes valeurs : (1) un bon concept Ramadan doit être partageable sans risquer ta crédibilité, (2) tu protèges la confiance de ton audience mixée (50% conservateurs / 50% modernes), (3) tu repères vite les concepts qui peuvent backfirer (tu as vu plusieurs marques se prendre des bides en 2024), (4) tu privilégies les concepts qui ont une « moment Instagram-able » fort, (5) tu refuses les concepts qui te font passer pour cynique.

Tes sources d'autorité : tendances TikTok globales (#RamadanVibes, #IftarMoments), tes pairs créatrices Maghreb, son audience DM (qu'elle sonde discrètement).

Au cours des 3 jours : tu testes en story (sondages) J1, tu décides quel concept tu vas partager J2 (selon le résultat sondage + l'event H+12), tu publies ou non J3. Tu écris en français + darija tunisienne ponctuelle, ton chaleureux et léger, beaucoup d'emojis. Tu utilises des hashtags trends.
```

## 5. Director events — injection text complet (US-040)

### 5.1. J1-H+12 (round 3) — `organic_amp`

```
[Injection round J1-H+12, 14h00] Une influenceuse tier-2 du marché marocain (88k followers Twitter/X, 120k followers Instagram, axée lifestyle famille), qui n'a pas été briefée par la marque, partage spontanément le Concept B « Solidarité quartier » avec un commentaire « Cette pub me rappelle les Ramadans de mon enfance à Salé. Le quartier qui partage, c'est ce qui me manque le plus à Casa. ❤️ ». Le post obtient 1200 likes en 2 heures et déclenche un fil de réactions partagées entre nostalgie et dénonciation du « cliché passéiste ».

Comment chaque persona réagit-il à cette amplification organique en faveur du Concept B ? Les modernes-progressistes (Sara) saluent-ils l'authenticité du moment ou critiquent-ils la nostalgie facile ? Les conservateurs religieux (Chouaib, Khadija) sont-ils plus favorables à B grâce à ce signal ? Les diaspora-critiques (Réda) y voient-ils un cliché à analyser ? L'ranking A vs B vs C bouge-t-il significativement ?
```

### 5.2. J1-H+20 (round 5) — `religious_backfire`

```
[Injection round J1-H+20, 22h00] Le Concept C « Humour des courses Ramadan » est partagé sur un groupe Facebook conservateur (12k membres, « Familles musulmanes du Maroc ») par un membre indigné qui juge les blagues du concept comme « manquant gravement de respect au mois saint, à la spiritualité, et aux familles modestes qui peinent déjà à boucler leurs courses ». Le post recueille 480 commentaires en 3 heures, dont 92% partagent l'indignation. Plusieurs commentaires appellent au boycott de la marque.

Une heure plus tard, deux figures religieuses suivies sur Facebook (un imam de Casablanca, une enseignante de l'Université d'Al Quaraouiyine) reprennent l'angle critique avec des arguments théologiques. Comment chaque persona réagit-il ? Les modernes-progressistes prennent-ils la défense du Concept C par principe créatif ou se distancient-ils ? Le ranking C s'effondre-t-il drastiquement ou les défenseurs du concept stabilisent-ils ?
```

### 5.3. J2-H+8 (round 8) — `competitor_launch`

```
[Injection round J2-H+8, 10h00] Le compétiteur direct de notre marque (groupe pan-africain équivalent, mêmes parts de marché Maroc) lance officiellement SA campagne Ramadan 2026 le matin. Concept compétiteur : film 30s « Iftar des inconnus » — montage documentaire de personnes invitant des inconnus à leur table d'iftar, ton sobre traditionnel mais avec un twist actuel (multi-générations, mixité urbaine). Production cinéma sobre, voix-off discrète, signature simple « Au-delà des liens du sang ».

La campagne compétiteur est immédiatement bien reçue (1500 likes Facebook + 800 retweets en 90 minutes), saluée comme « élégante » par plusieurs comptes trade et lifestyle. Comment chaque persona repositionne-t-il nos 3 concepts en référence à celui du compétiteur ? Le Concept A « Famille à table » est-il maintenant perçu comme « plus convenu et moins audacieux » ? Le Concept B « Solidarité quartier » est-il vu comme « moins fort que celui du compétiteur sur la même thématique » ? Le Concept C « Humour des courses » est-il vu comme « audacieux mais à risque » par contraste ?
```

### 5.4. J2-H+16 (round 10) — `budget_cut`

```
[Injection round J2-H+16, 18h00] Coup de fil interne du DG de la marque au lead marketing : un audit budget impose le retrait d'un concept sur les 3 (économie 60 000 USD sur la production + diffusion). Le DG demande une recommandation argumentée d'ici demain matin sur quel concept retirer.

Les 3 observateurs trade et les analystes concurrentiels réagissent à la fuite de cette information (qui a fuité via un consultant freelance) : leurs prédictions du concept à retirer divergent. Plusieurs personas du cœur d'audience expriment publiquement leur préférence sur quel concept doit être retiré.

Comment chaque persona se positionne-t-il sur le retrait recommandé ? Les religieux traditionnels recommandent-ils unanimement le retrait du Concept C ? Les modernes-progressistes défendent-ils le Concept B ? Les diaspora-critiques recommandent-ils le retrait du Concept A par principe ? Y a-t-il un consensus inter-segments ou un pur clivage ?
```

### 5.5. J3-H+4 (round 13) — `brand_qa`

```
[Injection round J3-H+4, 06h00] Plusieurs comptes Twitter/X de l'audience cible posent publiquement des questions au compte officiel de la marque sur le Concept B « Solidarité quartier » : « D'où viennent les acteurs de la saynète ? c'est filmé où exactement ? est-ce que c'est sponsorisé ou tourné en vrai ? est-ce que les habitants du quartier filmé ont été rémunérés correctement ? ». Les questions sont relayées par 4 journalistes trade et 2 doctorants diaspora qui demandent transparence.

L'équipe community management de la marque a 4 heures pour répondre publiquement avant que le silence ne devienne l'événement. Comment chaque persona réagit-il à cette demande de transparence ? Les modernes-progressistes saluent-ils la pression légitime ou y voient-ils du « bruit excessif » ? Les conservateurs religieux trouvent-ils la demande de transparence comme étrangère à la spiritualité Ramadan ? La perception du Concept B se renforce-t-elle (transparence assumée) ou s'effondre-t-elle (suspicion de mise en scène) ?
```

## 6. Verdict shape attendu (US-041)

```json
{
  "ranking": [
    {"concept": "B", "score": 72.5, "rank": 1},
    {"concept": "A", "score": 68.0, "rank": 2},
    {"concept": "C", "score": 32.0, "rank": 3}
  ],
  "per_concept_top_arguments": {
    "A": [
      "Chaleur familiale authentique (résonance forte chez Khadija et 23 pairs religieux modérés à conservateurs)",
      "Sécurité de positionnement (aucun risque de bad buzz, choix conservateur classique)",
      "Mémorisation visuelle élevée (table familiale = trope universel marocain)"
    ],
    "B": [
      "Modernité progressiste assumée (Sara + 19 pairs progressistes, score d'engagement +28% vs A)",
      "Amplification organique gratuite via influenceuse tier-2 (event J1-H+12)",
      "Multi-générations + mixité urbaine résonne avec audience cible 25-45 ans"
    ],
    "C": [
      "Originalité de ton (différencie la marque dans un océan de concepts traditionnels)",
      "Engagement séculaire moderne fort (Yassine + 14 pairs séculaires)",
      "Potentiel viral mème en cas de pic positif"
    ]
  },
  "per_concept_top_objections": {
    "A": [
      "Convenu, déjà-vu, faible audace créative (5 critiques chez modernes progressistes)",
      "Cliché passéiste (commenté par 4 doctorants diaspora)",
      "Légèrement éclipsé par concept compétiteur sobre (event J2-H+8 effet -7 points)"
    ],
    "B": [
      "Suspicion de mise en scène et opacité production (event J3-H+4 menace -12 points si non géré)",
      "Cliché « solidarité de quartier » potentiellement caricatural (analyse Réda)",
      "Recouvre la même thématique que la pub compétiteur (event J2-H+8 dilue la différenciation)"
    ],
    "C": [
      "Shit-storm religieux confirmé (event J1-H+20, -32 points score backfire)",
      "Manque de respect perçu par 8 religieux traditionnels et au moins 60 pairs implicites",
      "Audacieux mais segment cible trop étroit pour budget Ramadan grand public"
    ]
  },
  "backfire_risk": {
    "concept": "C",
    "probability_of_negative_buzz": 0.82,
    "magnitude_estimated": "Modéré à fort — peut générer un boycott temporaire de 2-3 semaines, image de marque écornée 6-9 mois sur le segment religieux conservateur (28% de la base clientèle).",
    "cause_racine": "Transgression du registre spirituel Ramadan par l'humour. Les acheteurs marocains 25-45 ans sont, à 67% selon les sondages 2024, soit pratiquants soit liés affectivement au respect des codes Ramadan ; un humour trop irrévérent sur les rituels (ici les courses massives) déclenche un effet identitaire défensif quasi automatique.",
    "mitigation_si_maintien": [
      "Retravailler le ton (humour bienveillant plutôt qu'irrévérent)",
      "Diffuser uniquement sur digital ciblé 25-35 ans urbain (pas TV grand public)",
      "Préparer un plan de réponse prêt en 4h en cas de bad buzz"
    ]
  },
  "recommendation": {
    "primary_action": "Diffuser Concept B en TV principal + digital national. Concept A en TV secondaire + radio. Retirer Concept C ou le repositionner en digital ciblé jeune urbain uniquement avec ton retravaillé.",
    "secondary_action_J3_QA": "Préparer une réponse transparente à la Q&A audience Concept B sous 2h : credits production + lieu tournage + budget acteurs réels (pas sponsorisés). Cela transforme la demande de transparence en argument de marque.",
    "competitor_response": "Différencier le Concept B de la pub compétiteur en mettant en avant l'angle 'multi-générations urbaines moderne' vs leur angle 'au-delà des liens du sang' plus traditionnel."
  },
  "narrative_summary": "[À générer par ReportAgent — 200-300 mots récit du test, points de bascule, recommandation finale au DG.]"
}
```

## 7. Notes d'implémentation

- 60 agents = 6 archétypes × 10 instances variées (âges précis, villes spécifiques, secteurs).
- Director events injectés à la frontière du round.
- Variants A/B/C des concepts pub testés simultanément en runs parallèles (3 sub-simulations) avec graine identique pour comparer.
- Le `narrative_summary` final est généré par `ReportAgent`.
