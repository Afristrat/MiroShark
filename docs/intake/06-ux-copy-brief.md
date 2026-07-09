# 06 — Brief UX et copy du module Intake

> S'inscrit dans la marque Bassira (docs/06-brand-brief.md, palette Causse « Warm
> Intelligence », tokens `--wi-*`). Ce document fixe le TON et les gabarits — les
> formulations finales fr/en/ar se valident à l'implémentation (parité même commit).

## Ton

- **Sobre, institutionnel, factuel** — le prospect est un décideur, pas un « user ».
- **Jamais prédictif** (ADR-002) : ni « nous prédirons », ni « précision », ni chiffres de
  calibration. Vocabulaire autorisé : stress-test, angles morts, réactions simulées,
  scénarios.
- **Réciprocité systématique** : chaque temps du formulaire affiche en une ligne pourquoi
  on demande (« Ces éléments calibrent votre scénario — rien n'est publié »).
- **Vouvoiement** en français ; registre équivalent en arabe (فصحى professionnelle, pas de
  darija dans le copy — l'agent, lui, COMPREND la darija si le prospect l'utilise).

## Principes UX

1. **3 écrans, un temps par écran**, barre de progression discrète (1/3 → 3/3). Jamais les
   8 questions sur une page.
2. **L'agent est un écran à part**, clairement optionnel : « Affiner votre brief avec
   notre assistant (2-3 minutes) » + bouton « Passer directement ». Bandeau permanent
   double mention : « Vous échangez avec l'assistant de qualification Bassira — une IA.
   Cet échange fait partie de votre dossier et nourrit votre devis. » (AI Act art. 50 +
   transparence ADR-IQ-07).
2bis. **La réservation d'entretien** (branche entretien) s'affiche dans la langue de
   session : le lien Cal.com généré porte le paramètre de locale, et le nom de l'event
   type est localisé. Règle transversale : AUCUNE sortie (écran, email, page de
   réservation, devis) dans une autre langue que celle choisie par l'utilisateur.
3. **Le flag confidentiel est un moment d'UX, pas une case** : quand l'agent propose de
   différer un sujet, le prospect voit une pastille « 🔒 Réservé à l'échange de vive
   voix » s'ajouter à une liste visible — la confidentialité devient une preuve de sérieux
   perçue, pas une friction.
4. **RTL intégral** en arabe (patterns existants : `inset-inline-*`, `:global([dir='rtl'])`).
5. **Mobile-first** : les décideurs MENA ouvrent sur téléphone ; le chat de l'étape B doit
   être utilisable au pouce.
6. **Aucun dark pattern** : « Passer » toujours visible, jamais de compte requis, jamais
   de champ piégé.

## Gabarits de copy (français — base de parité)

| Élément | Gabarit |
|---|---|
| Titre parcours | « Votre décision, d'abord. » |
| Temps 1 intro | « Trois questions sur la décision que vous devez prendre — pas sur nous. » |
| A1 label | « Quelle décision devez-vous prendre ? » + placeholder : « Ex. : lancer la filiale Sénégal maintenant ou attendre 2027 » |
| A4 label | « La dernière fois que vous avez pris une décision de ce poids, qu'est-ce qui vous a éclairé ? » |
| Agent, 1ᵉʳ message | « Bonjour — je suis l'assistant de qualification de Bassira, une intelligence artificielle. Quelques questions pour affiner votre brief ; si un sujet est confidentiel, dites-le : je le noterai pour votre échange de vive voix, sans le détailler ici. » |
| Flag confidentiel | « Noté — ce sujet sera abordé de vive voix. Il n'apparaîtra pas dans ce brief. » |
| Fin de parcours (branche entretien) | « Votre brief est prêt. Prochaine étape : 20 minutes avec notre équipe — nous arrivons préparés, vous ne répéterez rien. » |
| Porte 2 (AAR) | « Vous hésitez ? Testez Bassira sur une décision déjà tranchée dont vous connaissez l'issue. Vous jugerez sur pièce. » |
| Email objet (branche devis) | « Votre brief Bassira — [décision A1 tronquée à 60 c.] » |

## Anti-patterns de copy (interdits — revue systématique)

- « Seriez-vous intéressé par… » (question dont la réponse est toujours oui).
- « Quel est votre budget pour cette étude ? » (ancrage — on capte l'enjeu A6, jamais le
  budget alloué à Bassira).
- Tout compliment sollicité (« Que pensez-vous de notre approche ? »).
- Toute promesse de résultat (« vous saurez si votre lancement réussira »).
- « Gratuit », « sans engagement » répétés (dévalorise le palier d'entrée payant).

## Livrables design attendus (avant code)

- Maquettes Stitch des 4 écrans (3 temps + agent) — prompt fourni dans le doc 10.
- Revue de parité fr/en/ar sur tableau de clés AVANT intégration.
