# Bassira — Apollo CRM Outreach Sequences

> 3 séquences ciblant Strategy Directors / CEOs / CFOs MENA + Europe.
> Tone : consultatif, pas salesy. Brand voice Bassira (Outfit/Manrope, palette Causse).
>
> **Bassira (بصيرة)** — plateforme SaaS de simulation stratégique multi-agents. Brier score 0,18. Calibration vérifiable. Decisions au lieu de slides.
>
> **Palette de référence (Causse)** : `#FAF7F2` (cream surface) · `#A13F0F` (terracotta CTA) · `#241915` (warm charcoal text) · `#006D44` (mint trust) · `#8A7269` (muted footer).
>
> **Typographie** : Outfit (titres, 500/600), Manrope (corps, 400/500), Tajawal (arabe, 400/500), JetBrains Mono (données techniques).
>
> **Conventions copywriting** :
> - Phrases courtes, busy C-Levels (≤ 3 phrases utiles par email).
> - 1 idée par email, 1 CTA, 1 lien.
> - JAMAIS « AI-powered », « cutting-edge », « leverages », « revolutionary », « game-changer », « disruptive ».
> - Signature : « — Amine, Bassira » (pas de titre).
> - From : Amine Mansouri Idrissi <amine@bassira.com>.
>
> **Conventions HTML** :
> - Inline CSS uniquement (compatibilité Outlook/Gmail/Apollo).
> - Largeur max 600 px (table-based layout).
> - CTA : `background:#A13F0F; color:#FAF7F2; border-radius:12px; padding:12px 24px`.
> - Footer Manrope 12 px `#8A7269`.
> - Variables Apollo : `{{first_name}}`, `{{company_name}}`, `{{trigger_event}}`, `{{recent_sector_event}}`.

---

## Index

| Séquence | Trigger | Tone | Cadence | Emails | LinkedIn |
|----------|---------|------|---------|--------|----------|
| 1 — Pre-Decision Anxiety | Annonce M&A, lancement, élection | Urgence consultative | J0 + J3 + J7 | 3 × FR/EN/AR | 2 (court + long) |
| 2 — Blindspot Post-Crisis | Choc sectoriel récent, post-mortem | Lucidité froide | J0 + J4 + J9 | 3 × FR/EN/AR | 2 (court + long) |
| 3 — Calibration Proof | Trust-building data-driven | Preuve technique | J0 + J5 + J11 | 3 × FR/EN/AR | 2 (court + long) |

---

# SEQUENCE 1 — Pre-Decision Anxiety

**Trigger** : prospect a annoncé une décision majeure (M&A, lancement produit majeur, restructuration, élection sectorielle, fundraising round, IPO).

**Tone** : urgence consultative. Pas alarmiste, pas vendeur. On reformule sa décision et on lui montre qu'il n'a probablement pas modélisé tous les scénarios.

**Hook formula** : `[Event annoncé] → [Risk narratif/comportemental non modélisé] → [Bassira simule X scénarios en Y heures]`

**Cadence** : J0 (cold) → J3 (follow-up valeur) → J7 (break-up).

**ICP** : Strategy Directors, CEOs, CFOs, Heads of M&A, Conseil stratégique de comités de direction (CAC 40, MASI, FTSE 100, GCC family offices).

---

## SEQUENCE 1 — Email 1 — Cold (J0)

### Email 1.1.FR — Cold (français)

**Subject** : Stress-test stratégique avant votre {{trigger_event}}

**From** : Amine Mansouri Idrissi <amine@bassira.com>

**Plain text version**

```
Bonjour {{first_name}},

L'annonce de {{trigger_event}} chez {{company_name}} comporte une volatilité narrative importante — celle qu'aucun modèle financier classique ne capture.

Nous avons simulé 10 000 interactions d'agents (régulateurs, concurrents, presse, syndicats) pour identifier les vecteurs de risque cachés sur ce type de décision. Le rapport de stress-test est ici : https://bassira.com/calibration?ref=apollo-s1e1

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stress-test stratégique</title>
</head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, -apple-system, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px; background-color:#FAF7F2;">
          <tr>
            <td style="padding-bottom:24px; font-family:'Outfit', system-ui, -apple-system, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">
              Bassira
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
              Bonjour {{first_name}},
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
              L'annonce de <strong>{{trigger_event}}</strong> chez {{company_name}} comporte une volatilité narrative importante — celle qu'aucun modèle financier classique ne capture.
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
              Nous avons simulé 10 000 interactions d'agents (régulateurs, concurrents, presse, syndicats) pour identifier les vecteurs de risque cachés sur ce type de décision.
            </td>
          </tr>
          <tr>
            <td align="left" style="padding-bottom:32px;">
              <a href="https://bassira.com/calibration?ref=apollo-s1e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
                Consulter le stress-test
              </a>
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">
              — Amine, Bassira
            </td>
          </tr>
          <tr>
            <td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
              Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
              Casablanca · Paris · Dubaï · Londres · Riyad.<br>
              <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

---

### Email 1.1.EN — Cold (English)

**Subject** : Stress-test before your {{trigger_event}}

**From** : Amine Mansouri Idrissi <amine@bassira.com>

**Plain text version**

```
Hi {{first_name}},

The {{trigger_event}} announcement at {{company_name}} carries significant narrative volatility — the kind no classical financial model captures.

We simulated 10,000 agent interactions (regulators, competitors, press, unions) to surface the hidden risk vectors on this type of move. Stress-test results here: https://bassira.com/calibration?ref=apollo-s1e1

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Strategic stress-test</title>
</head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, -apple-system, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px; background-color:#FAF7F2;">
          <tr>
            <td style="padding-bottom:24px; font-family:'Outfit', system-ui, -apple-system, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">
              Bassira
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
              Hi {{first_name}},
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
              The <strong>{{trigger_event}}</strong> announcement at {{company_name}} carries significant narrative volatility — the kind no classical financial model captures.
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
              We simulated 10,000 agent interactions (regulators, competitors, press, unions) to surface the hidden risk vectors on this type of move.
            </td>
          </tr>
          <tr>
            <td align="left" style="padding-bottom:32px;">
              <a href="https://bassira.com/calibration?ref=apollo-s1e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
                Review stress-test results
              </a>
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">
              — Amine, Bassira
            </td>
          </tr>
          <tr>
            <td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
              Bassira — Strategic Foresight for MENA &amp; Europe.<br>
              Casablanca · Paris · Dubai · London · Riyadh.<br>
              <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

---

### Email 1.1.AR — Cold (العربية)

**Subject** : اختبار إجهاد استراتيجي قبل {{trigger_event}}

**From** : Amine Mansouri Idrissi <amine@bassira.com>

**Plain text version**

```
سيدي {{first_name}}،

إعلان {{trigger_event}} لدى {{company_name}} يحمل تقلبات سردية كبيرة لا يلتقطها أي نموذج مالي تقليدي.

قمنا بمحاكاة 10,000 تفاعل بين وكلاء (هيئات تنظيمية، منافسون، صحافة، نقابات) لكشف نقاط الخطر الخفية في هذا النوع من القرارات. نتائج الاختبار هنا: https://bassira.com/calibration?ref=apollo-s1e1

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>اختبار إجهاد استراتيجي</title>
</head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', 'Manrope', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px; background-color:#FAF7F2;">
          <tr>
            <td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F; letter-spacing:0.04em;">
              بَصِيرَة
            </td>
          </tr>
          <tr>
            <td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
              سيدي {{first_name}}،
            </td>
          </tr>
          <tr>
            <td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
              إعلان <strong>{{trigger_event}}</strong> لدى {{company_name}} يحمل تقلبات سردية كبيرة لا يلتقطها أي نموذج مالي تقليدي.
            </td>
          </tr>
          <tr>
            <td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
              قمنا بمحاكاة 10,000 تفاعل بين وكلاء (هيئات تنظيمية، منافسون، صحافة، نقابات) لكشف نقاط الخطر الخفية في هذا النوع من القرارات.
            </td>
          </tr>
          <tr>
            <td align="right" style="padding-bottom:32px;">
              <a href="https://bassira.com/calibration?ref=apollo-s1e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
                الاطلاع على نتائج الاختبار
              </a>
            </td>
          </tr>
          <tr>
            <td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">
              — أمين، بصيرة
            </td>
          </tr>
          <tr>
            <td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
              بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
              الدار البيضاء · باريس · دبي · لندن · الرياض.<br>
              <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 1 — Email 2 — Follow-up (J3)

### Email 1.2.FR — Follow-up (français)

**Subject** : 3 scénarios que votre comité n'a pas encore vus

**From** : Amine Mansouri Idrissi <amine@bassira.com>

**Plain text version**

```
{{first_name}},

J'ai relu mon email de lundi — il était trop générique. Concrètement : sur les 10 000 simulations que nous avons fait tourner pour des opérations comparables à {{trigger_event}}, 3 scénarios reviennent systématiquement et sont rarement modélisés en interne :

— Réaction asymétrique d'un régulateur après une fuite presse.
— Bascule de narratif d'un syndicat ou d'un actionnaire activiste à J+30.
— Effet domino sur deux concurrents qui anticipent votre move.

Chacun de ces scénarios coûte entre 0,5 % et 4 % de capitalisation post-deal. La fiche détaillée est ici : https://bassira.com/explore?ref=apollo-s1e2

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>3 scénarios</title>
</head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
          <tr>
            <td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
              J'ai relu mon email de lundi — il était trop générique. Concrètement : sur les 10 000 simulations que nous avons fait tourner pour des opérations comparables à <strong>{{trigger_event}}</strong>, 3 scénarios reviennent systématiquement et sont rarement modélisés en interne :
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.7; color:#241915; padding:0 0 16px 16px;">
              — Réaction asymétrique d'un régulateur après une fuite presse.<br>
              — Bascule de narratif d'un syndicat ou d'un actionnaire activiste à J+30.<br>
              — Effet domino sur deux concurrents qui anticipent votre move.
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
              Chacun de ces scénarios coûte entre 0,5 % et 4 % de capitalisation post-deal.
            </td>
          </tr>
          <tr>
            <td align="left" style="padding-bottom:32px;">
              <a href="https://bassira.com/explore?ref=apollo-s1e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
                Voir les 3 scénarios
              </a>
            </td>
          </tr>
          <tr>
            <td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td>
          </tr>
          <tr>
            <td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
              Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
              <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

---

### Email 1.2.EN — Follow-up (English)

**Subject** : 3 scenarios your board hasn't seen yet

**From** : Amine Mansouri Idrissi <amine@bassira.com>

**Plain text version**

```
{{first_name}},

Re-reading my Monday note — it was too generic. Concretely: across the 10,000 simulations we ran on deals comparable to {{trigger_event}}, three scenarios show up systematically and rarely sit in internal models:

— Asymmetric regulator response after a press leak.
— Narrative flip from a union or activist shareholder at D+30.
— Domino effect on two competitors anticipating your move.

Each scenario costs between 0.5% and 4% of post-deal capitalisation. Detailed brief here: https://bassira.com/explore?ref=apollo-s1e2

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>3 scenarios</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Re-reading my Monday note — it was too generic. Across the 10,000 simulations we ran on deals comparable to <strong>{{trigger_event}}</strong>, three scenarios show up systematically and rarely sit in internal models:
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.7; color:#241915; padding:0 0 16px 16px;">
          — Asymmetric regulator response after a press leak.<br>
          — Narrative flip from a union or activist shareholder at D+30.<br>
          — Domino effect on two competitors anticipating your move.
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          Each scenario costs between 0.5% and 4% of post-deal capitalisation.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/explore?ref=apollo-s1e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            See the 3 scenarios
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight for MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 1.2.AR — Follow-up (العربية)

**Subject** : ثلاثة سيناريوهات لم يرها مجلسكم بعد

**From** : Amine Mansouri Idrissi <amine@bassira.com>

**Plain text version**

```
{{first_name}}،

أعدت قراءة رسالتي الأولى — كانت عامة أكثر من اللازم. بشكل ملموس: من بين 10,000 محاكاة أجريناها على عمليات مماثلة لـ {{trigger_event}}، ثلاثة سيناريوهات تتكرر باستمرار ونادرا ما تُنمذج داخليا:

— استجابة غير متناظرة من جهة تنظيمية بعد تسريب صحفي.
— انقلاب سردي من نقابة أو مساهم ناشط في اليوم 30.
— تأثير الدومينو على منافسَين يتوقعان تحرككم.

كل سيناريو يكلف بين 0,5 % و4 % من الرسملة بعد الصفقة. التفاصيل: https://bassira.com/explore?ref=apollo-s1e2

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ثلاثة سيناريوهات</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px;">
        <tr><td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F;">بَصِيرَة</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">{{first_name}}،</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          أعدت قراءة رسالتي الأولى — كانت عامة أكثر من اللازم. من بين 10,000 محاكاة أجريناها على عمليات مماثلة لـ <strong>{{trigger_event}}</strong>، ثلاثة سيناريوهات تتكرر باستمرار ونادرا ما تُنمذج داخليا:
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.9; color:#241915; padding:0 16px 16px 0;">
          — استجابة غير متناظرة من جهة تنظيمية بعد تسريب صحفي.<br>
          — انقلاب سردي من نقابة أو مساهم ناشط في اليوم 30.<br>
          — تأثير الدومينو على منافسَين يتوقعان تحرككم.
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
          كل سيناريو يكلف بين 0,5 % و4 % من الرسملة بعد الصفقة.
        </td></tr>
        <tr><td align="right" style="padding-bottom:32px;">
          <a href="https://bassira.com/explore?ref=apollo-s1e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
            الاطلاع على السيناريوهات الثلاثة
          </a>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">— أمين، بصيرة</td></tr>
        <tr><td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
          بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 1 — Email 3 — Break-up (J7)

### Email 1.3.FR — Break-up (français)

**Subject** : Je ferme votre dossier {{company_name}}

**Plain text version**

```
{{first_name}},

Pas de réponse — c'est ok, votre {{trigger_event}} occupe sans doute toute votre bande passante.

Je ferme votre dossier de mon côté. Si à un moment vous voulez voir, en 30 minutes, ce que 10 000 agents disent de vos prochains arbitrages — vous avez ce lien : https://bassira.com/calibration?ref=apollo-s1e3-breakup

Bonne suite sur cette opération.

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Clôture dossier</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Pas de réponse — c'est ok, votre <strong>{{trigger_event}}</strong> occupe sans doute toute votre bande passante.
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          Je ferme votre dossier de mon côté. Si à un moment vous voulez voir, en 30 minutes, ce que 10 000 agents disent de vos prochains arbitrages — vous avez ce lien.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration?ref=apollo-s1e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Lancer une simulation à blanc
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:8px;">Bonne suite sur cette opération.</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 1.3.EN — Break-up (English)

**Subject** : Closing your {{company_name}} file

**Plain text version**

```
{{first_name}},

No reply — fair enough, {{trigger_event}} is probably eating all your bandwidth.

I'm closing the file on my side. If at some point you want to see, in 30 minutes, what 10,000 agents say about your next strategic calls — the link stays open: https://bassira.com/calibration?ref=apollo-s1e3-breakup

Good luck on the deal.

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Closing your file</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          No reply — fair enough, <strong>{{trigger_event}}</strong> is probably eating all your bandwidth.
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          I'm closing the file on my side. If at some point you want to see, in 30 minutes, what 10,000 agents say about your next strategic calls — the link stays open.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration?ref=apollo-s1e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Run a dry-run simulation
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:8px;">Good luck on the deal.</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight for MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 1.3.AR — Break-up (العربية)

**Subject** : إغلاق ملف {{company_name}}

**Plain text version**

```
{{first_name}}،

لم يصلني رد — لا بأس، {{trigger_event}} يستحوذ على كامل وقتكم على الأرجح.

أغلق الملف من جهتي. إذا أردتم في وقت لاحق رؤية ما يقوله 10,000 وكيل ذكي عن قراراتكم القادمة، خلال 30 دقيقة فقط، الرابط يبقى مفتوحا: https://bassira.com/calibration?ref=apollo-s1e3-breakup

بالتوفيق في هذه العملية.

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>إغلاق الملف</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px;">
        <tr><td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F;">بَصِيرَة</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">{{first_name}}،</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          لم يصلني رد — لا بأس، <strong>{{trigger_event}}</strong> يستحوذ على كامل وقتكم على الأرجح.
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
          أغلق الملف من جهتي. إذا أردتم في وقت لاحق رؤية ما يقوله 10,000 وكيل ذكي عن قراراتكم القادمة، خلال 30 دقيقة فقط، الرابط يبقى مفتوحا.
        </td></tr>
        <tr><td align="right" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration?ref=apollo-s1e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
            تشغيل محاكاة تجريبية
          </a>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:8px;">بالتوفيق في هذه العملية.</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">— أمين، بصيرة</td></tr>
        <tr><td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
          بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 1 — LinkedIn DMs

### LinkedIn DM 1 — Court (≤ 500 caractères)

```
Bonjour {{first_name}},

Vu l'annonce de {{trigger_event}} chez {{company_name}}. Sur ce type d'opération, 3 scénarios narratifs cassent la valeur post-deal et sont rarement modélisés (régulateur, activistes, dominos concurrents).

On les a stress-testés sur 10 000 agents simulés. Si ça vous intéresse de voir le rapport en 5 min, je vous l'envoie.

— Amine, Bassira
```

(498 caractères)

### LinkedIn DM 2 — Long (≤ 1300 caractères)

```
Bonjour {{first_name}},

Je suis tombé sur l'annonce de {{trigger_event}} chez {{company_name}}. Pas un cold pitch — juste une observation : sur les opérations de cette nature, ce qui casse la valeur post-deal vient rarement du modèle financier. Ça vient du narratif.

Concrètement, sur les 10 000 simulations multi-agents que nous avons fait tourner pour des deals comparables, trois scénarios reviennent quasi-systématiquement et sont rarement dans les decks de comité :

1. Réaction asymétrique d'un régulateur après une fuite presse à J+5.
2. Bascule d'un syndicat ou d'un actionnaire activiste vers J+30.
3. Effet domino sur deux concurrents qui anticipent et préemptent.

Coût moyen observé : entre 0,5 % et 4 % de la cap post-deal.

Bassira simule ces interactions (régulateurs, presse, syndicats, concurrents) avec un Brier score de 0,18 — calibration vérifiable, pas un Monte-Carlo opaque.

Si vous voulez voir, en 30 min de votre temps, à quoi ça ressemble pour {{company_name}}, je peux envoyer le rapport. Pas d'obligation derrière.

— Amine, Bassira
```

(1281 caractères)

---

# SEQUENCE 2 — Blindspot Post-Crisis

**Trigger** : un secteur ou un acteur proche du prospect vient de subir un choc (effondrement boursier, scandale ESG, crise réputationnelle, faillite, sanction réglementaire).

**Tone** : lucidité froide. Pas accusateur, pas opportuniste. On reformule le post-mortem du choc et on pose la question : « combien d'autres scénarios non modélisés dorment dans votre comité ? ».

**Hook formula** : `[Choc sectoriel récent] → [Personne ne l'avait simulé] → [Bassira ouvre le post-mortem en open access]`

**Cadence** : J0 (cold) → J4 (post-mortem détaillé) → J9 (break-up).

---

## SEQUENCE 2 — Email 1 — Cold (J0)

### Email 2.1.FR — Cold (français)

**Subject** : Post-mortem ouvert sur {{recent_sector_event}}

**Plain text version**

```
Bonjour {{first_name}},

Quand {{recent_sector_event}} a basculé, combien de scénarios comportementaux votre équipe avait-elle modélisés ?

Nous avons mis en open access une simulation post-mortem de l'événement — agents régulateurs, médias, concurrents, retail. Ça met en lumière les angles morts exacts que les modèles financiers classiques ratent.

Le rapport : https://bassira.com/explore/blindspot?ref=apollo-s2e1

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Post-mortem ouvert</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">Bonjour {{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Quand <strong>{{recent_sector_event}}</strong> a basculé, combien de scénarios comportementaux votre équipe avait-elle modélisés ?
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          Nous avons mis en open access une simulation post-mortem de l'événement — agents régulateurs, médias, concurrents, retail. Ça met en lumière les angles morts exacts que les modèles financiers classiques ratent.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/explore/blindspot?ref=apollo-s2e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Accéder au post-mortem
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
          Casablanca · Paris · Dubaï · Londres · Riyad.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 2.1.EN — Cold (English)

**Subject** : Open post-mortem on {{recent_sector_event}}

**Plain text version**

```
Hi {{first_name}},

When {{recent_sector_event}} unraveled, how many behavioural scenarios had your team modelled?

We've open-sourced a post-mortem simulation of the event — regulator agents, media, competitors, retail. It highlights the exact blindspots classical financial models miss.

The report: https://bassira.com/explore/blindspot?ref=apollo-s2e1

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Open post-mortem</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">Hi {{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          When <strong>{{recent_sector_event}}</strong> unraveled, how many behavioural scenarios had your team modelled?
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          We've open-sourced a post-mortem simulation of the event — regulator agents, media, competitors, retail. It highlights the exact blindspots classical financial models miss.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/explore/blindspot?ref=apollo-s2e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Access post-mortem
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight for MENA &amp; Europe.<br>
          Casablanca · Paris · Dubai · London · Riyadh.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 2.1.AR — Cold (العربية)

**Subject** : تحليل ما بعد الأزمة المفتوح حول {{recent_sector_event}}

**Plain text version**

```
سيدي {{first_name}}،

عندما انهار {{recent_sector_event}}، كم سيناريو سلوكي كان فريقكم قد نمذجه ؟

أتحنا للعموم محاكاة لتحليل ما بعد الأزمة لهذا الحدث — وكلاء الجهات التنظيمية، الإعلام، المنافسون، المستثمرون الأفراد. تكشف بدقة النقاط العمياء التي تتجاهلها النماذج المالية التقليدية.

التقرير: https://bassira.com/explore/blindspot?ref=apollo-s2e1

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>تحليل ما بعد الأزمة</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px;">
        <tr><td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F;">بَصِيرَة</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">سيدي {{first_name}}،</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          عندما انهار <strong>{{recent_sector_event}}</strong>، كم سيناريو سلوكي كان فريقكم قد نمذجه ؟
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
          أتحنا للعموم محاكاة لتحليل ما بعد الأزمة لهذا الحدث — وكلاء الجهات التنظيمية، الإعلام، المنافسون، المستثمرون الأفراد. تكشف بدقة النقاط العمياء التي تتجاهلها النماذج المالية التقليدية.
        </td></tr>
        <tr><td align="right" style="padding-bottom:32px;">
          <a href="https://bassira.com/explore/blindspot?ref=apollo-s2e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
            الاطلاع على التحليل
          </a>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">— أمين، بصيرة</td></tr>
        <tr><td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
          بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
          الدار البيضاء · باريس · دبي · لندن · الرياض.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 2 — Email 2 — Follow-up (J4)

### Email 2.2.FR — Follow-up (français)

**Subject** : Le scénario qui a fait basculer {{recent_sector_event}}

**Plain text version**

```
{{first_name}},

Petit retour sur le post-mortem.

Sur les 10 000 agents que nous avons fait tourner sur {{recent_sector_event}}, le scénario décisif n'était pas celui que la presse a raconté. C'est un agent retail (pas institutionnel) qui a déclenché la bascule à J+11, suivi par un effet de cascade sur les hedge funds.

Cet enchaînement précis n'apparaissait dans aucun deck de risk management que nous ayons consulté en post-event.

La fiche détaillée — avec le timing exact et les agents impliqués — est ici : https://bassira.com/explore/blindspot/cascade?ref=apollo-s2e2

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Le scénario décisif</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Petit retour sur le post-mortem. Sur les 10 000 agents que nous avons fait tourner sur <strong>{{recent_sector_event}}</strong>, le scénario décisif n'était pas celui que la presse a raconté.
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          C'est un agent <em>retail</em> (pas institutionnel) qui a déclenché la bascule à J+11, suivi par un effet de cascade sur les hedge funds. Cet enchaînement précis n'apparaissait dans aucun deck de risk management consulté en post-event.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/explore/blindspot/cascade?ref=apollo-s2e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Voir la cascade exacte
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 2.2.EN — Follow-up (English)

**Subject** : The scenario that flipped {{recent_sector_event}}

**Plain text version**

```
{{first_name}},

Quick follow-up on the post-mortem.

On the 10,000 agents we ran across {{recent_sector_event}}, the deciding scenario wasn't the one the press told. A retail agent (not an institutional one) triggered the flip at D+11, followed by a cascade across hedge funds.

That exact sequence wasn't in a single risk management deck we reviewed post-event.

Detailed breakdown — exact timing and agents involved: https://bassira.com/explore/blindspot/cascade?ref=apollo-s2e2

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>The deciding scenario</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Quick follow-up on the post-mortem. On the 10,000 agents we ran across <strong>{{recent_sector_event}}</strong>, the deciding scenario wasn't the one the press told.
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          A <em>retail</em> agent (not institutional) triggered the flip at D+11, followed by a cascade across hedge funds. That exact sequence wasn't in a single risk management deck we reviewed post-event.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/explore/blindspot/cascade?ref=apollo-s2e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            See the exact cascade
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight for MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 2.2.AR — Follow-up (العربية)

**Subject** : السيناريو الحاسم في {{recent_sector_event}}

**Plain text version**

```
{{first_name}}،

متابعة قصيرة لتحليل ما بعد الأزمة.

من بين 10,000 وكيل ذكي شغّلناهم على {{recent_sector_event}}، السيناريو الحاسم لم يكن ما روته الصحافة. وكيل أفراد (لا مؤسسي) هو من أشعل الانقلاب في اليوم 11، تلاه أثر تعاقبي على صناديق التحوط.

هذا التسلسل الدقيق لم يكن حاضرا في أي عرض إدارة مخاطر اطلعنا عليه بعد الحدث.

التحليل التفصيلي — التوقيت والوكلاء المشاركون: https://bassira.com/explore/blindspot/cascade?ref=apollo-s2e2

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>السيناريو الحاسم</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px;">
        <tr><td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F;">بَصِيرَة</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">{{first_name}}،</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          متابعة قصيرة لتحليل ما بعد الأزمة. من بين 10,000 وكيل ذكي شغّلناهم على <strong>{{recent_sector_event}}</strong>، السيناريو الحاسم لم يكن ما روته الصحافة.
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
          وكيل أفراد (لا مؤسسي) هو من أشعل الانقلاب في اليوم 11، تلاه أثر تعاقبي على صناديق التحوط. هذا التسلسل الدقيق لم يكن حاضرا في أي عرض إدارة مخاطر اطلعنا عليه بعد الحدث.
        </td></tr>
        <tr><td align="right" style="padding-bottom:32px;">
          <a href="https://bassira.com/explore/blindspot/cascade?ref=apollo-s2e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
            الاطلاع على التسلسل
          </a>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">— أمين، بصيرة</td></tr>
        <tr><td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
          بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 2 — Email 3 — Break-up (J9)

### Email 2.3.FR — Break-up (français)

**Subject** : Dernière note sur les angles morts

**Plain text version**

```
{{first_name}},

Je n'insisterai pas. Juste une question avant de fermer le dossier :

Sur les 10 prochains chocs sectoriels qui toucheront {{company_name}}, combien sont déjà dans vos modèles ?

Si la réponse est « moins de la moitié », le lien reste ouvert : https://bassira.com/calibration?ref=apollo-s2e3-breakup

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dernière note</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Je n'insisterai pas. Juste une question avant de fermer le dossier :
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:18px; line-height:1.6; color:#241915; padding-bottom:24px; font-style:italic;">
          Sur les 10 prochains chocs sectoriels qui toucheront <strong>{{company_name}}</strong>, combien sont déjà dans vos modèles ?
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          Si la réponse est « moins de la moitié », le lien reste ouvert.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration?ref=apollo-s2e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Calibrer mes scénarios
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 2.3.EN — Break-up (English)

**Subject** : Last note on blindspots

**Plain text version**

```
{{first_name}},

I won't push further. Just one question before I close the file:

Out of the next 10 sector shocks that will hit {{company_name}}, how many are already in your models?

If the honest answer is "less than half", the link stays open: https://bassira.com/calibration?ref=apollo-s2e3-breakup

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Last note on blindspots</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          I won't push further. Just one question before I close the file:
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:18px; line-height:1.6; color:#241915; padding-bottom:24px; font-style:italic;">
          Out of the next 10 sector shocks that will hit <strong>{{company_name}}</strong>, how many are already in your models?
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          If the honest answer is "less than half", the link stays open.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration?ref=apollo-s2e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Calibrate my scenarios
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight for MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 2.3.AR — Break-up (العربية)

**Subject** : ملاحظة أخيرة حول النقاط العمياء

**Plain text version**

```
{{first_name}}،

لن ألح أكثر. سؤال واحد قبل إغلاق الملف:

من بين الصدمات القطاعية العشر القادمة التي ستضرب {{company_name}}، كم منها مُنمذج فعلا في موديلاتكم ؟

إذا كانت الإجابة الصادقة "أقل من النصف"، الرابط يبقى مفتوحا: https://bassira.com/calibration?ref=apollo-s2e3-breakup

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ملاحظة أخيرة</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px;">
        <tr><td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F;">بَصِيرَة</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">{{first_name}}،</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          لن ألح أكثر. سؤال واحد قبل إغلاق الملف:
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:20px; line-height:1.8; color:#241915; padding-bottom:24px; font-style:italic;">
          من بين الصدمات القطاعية العشر القادمة التي ستضرب <strong>{{company_name}}</strong>، كم منها مُنمذج فعلا في موديلاتكم ؟
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
          إذا كانت الإجابة الصادقة "أقل من النصف"، الرابط يبقى مفتوحا.
        </td></tr>
        <tr><td align="right" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration?ref=apollo-s2e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
            معايرة سيناريوهاتي
          </a>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">— أمين، بصيرة</td></tr>
        <tr><td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
          بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 2 — LinkedIn DMs

### LinkedIn DM 1 — Court (≤ 500 caractères)

```
Bonjour {{first_name}},

Quand {{recent_sector_event}} a basculé, qui l'avait simulé ? Nous avons mis en open access le post-mortem multi-agents : un agent retail (pas institutionnel) déclenche la cascade à J+11.

Ça pose une vraie question pour {{company_name}}. Lien si ça vous intéresse.

— Amine, Bassira
```

(370 caractères)

### LinkedIn DM 2 — Long (≤ 1300 caractères)

```
Bonjour {{first_name}},

Je vous écris à froid, mais avec une vraie question — pas un pitch.

Quand {{recent_sector_event}} s'est effondré, qui dans la place l'avait modélisé ? Sur la trentaine de decks de risk management post-event que nous avons pu consulter, aucun n'avait simulé la séquence exacte. Le scénario décisif venait d'un agent retail (pas institutionnel) qui a déclenché la bascule à J+11, suivi d'une cascade sur les hedge funds.

Ce n'est pas un cas isolé. La majorité des chocs sectoriels suivent ce pattern : ce qui casse la valeur n'est jamais dans les decks, parce que les modèles classiques sous-pondèrent les agents non-institutionnels et la propagation narrative.

Bassira a mis en open access la simulation complète — 10 000 agents, timing précis, calibration vérifiable (Brier score 0,18). On l'utilise comme un miroir pour les comités de direction : sur les 10 prochains chocs qui toucheraient {{company_name}}, combien sont déjà dans vos modèles ?

Si vous voulez voir le post-mortem ou faire tourner un dry-run sur votre secteur, je peux vous l'ouvrir. Pas d'engagement.

— Amine, Bassira
```

(1213 caractères)

---

# SEQUENCE 3 — Calibration Proof

**Trigger** : trust-building data-driven. Ciblé sur les prospects techniques (CFOs, Heads of Quant Risk, Chief Strategy Officers) qui valorisent la preuve méthodologique avant la conversation commerciale.

**Tone** : preuve technique. On ouvre par un chiffre vérifiable (Brier score 0,18), pas par une question. La crédibilité passe avant la curiosité.

**Hook formula** : `[Métrique vérifiable] → [Pourquoi ça importe pour vos décisions] → [Rapport méthodologique téléchargeable]`

**Cadence** : J0 (cold) → J5 (méthodo détaillée) → J11 (break-up).

---

## SEQUENCE 3 — Email 1 — Cold (J0)

### Email 3.1.FR — Cold (français)

**Subject** : Brier score 0,18 — audit méthodologique Bassira

**Plain text version**

```
Bonjour {{first_name}},

La plupart des modèles de prévision stratégique ne sont jamais mesurés. Les nôtres le sont.

Notre Brier score actuel est de 0,18 sur 18 mois de prévisions historiques — soit une calibration vérifiable, supérieure à la médiane des prediction markets et largement au-dessus du baseline analyst consensus.

Le rapport méthodologique complet (jeu de test, validation, limites) est ici : https://bassira.com/calibration/methodology?ref=apollo-s3e1

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Brier 0,18 — audit</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">Bonjour {{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          La plupart des modèles de prévision stratégique ne sont jamais mesurés. Les nôtres le sont.
        </td></tr>
        <tr><td align="left" style="padding:0 0 24px 0;">
          <span style="display:inline-block; background-color:#FFE9E2; color:#7E2B00; font-family:'JetBrains Mono', Consolas, monospace; font-size:13px; font-weight:500; padding:6px 14px; border-radius:9999px; border:1px solid #DEC0B6;">
            Brier score : 0,18
          </span>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          Sur 18 mois de prévisions historiques — calibration vérifiable, supérieure à la médiane des prediction markets et largement au-dessus du baseline analyst consensus.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/methodology?ref=apollo-s3e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Télécharger le rapport méthodo
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
          Casablanca · Paris · Dubaï · Londres · Riyad.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 3.1.EN — Cold (English)

**Subject** : Brier score 0.18 — Bassira methodology audit

**Plain text version**

```
Hi {{first_name}},

Most strategic forecasting models are never measured. Ours are.

Our current Brier score is 0.18, across 18 months of historical forecasts — verifiable calibration, above the median of prediction markets, and well above the baseline analyst consensus.

Full methodology report (test set, validation, limitations) here: https://bassira.com/calibration/methodology?ref=apollo-s3e1

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Brier 0.18 — audit</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">Hi {{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Most strategic forecasting models are never measured. Ours are.
        </td></tr>
        <tr><td align="left" style="padding:0 0 24px 0;">
          <span style="display:inline-block; background-color:#FFE9E2; color:#7E2B00; font-family:'JetBrains Mono', Consolas, monospace; font-size:13px; font-weight:500; padding:6px 14px; border-radius:9999px; border:1px solid #DEC0B6;">
            Brier score: 0.18
          </span>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          Across 18 months of historical forecasts — verifiable calibration, above the median of prediction markets, and well above the baseline analyst consensus.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/methodology?ref=apollo-s3e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Download methodology report
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight for MENA &amp; Europe.<br>
          Casablanca · Paris · Dubai · London · Riyadh.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 3.1.AR — Cold (العربية)

**Subject** : درجة براير 0.18 — تدقيق منهجي لبصيرة

**Plain text version**

```
سيدي {{first_name}}،

معظم نماذج التنبؤ الاستراتيجي لا تُقاس أبدا. نماذجنا تُقاس.

درجة براير الحالية لدينا هي 0.18 على 18 شهرا من التنبؤات التاريخية — معايرة قابلة للتحقق، أعلى من وسيط أسواق التنبؤ، وأعلى بكثير من خط أساس إجماع المحللين.

تقرير المنهجية الكامل (مجموعة الاختبار، التحقق، الحدود): https://bassira.com/calibration/methodology?ref=apollo-s3e1

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>درجة براير 0.18</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px;">
        <tr><td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F;">بَصِيرَة</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">سيدي {{first_name}}،</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          معظم نماذج التنبؤ الاستراتيجي لا تُقاس أبدا. نماذجنا تُقاس.
        </td></tr>
        <tr><td align="right" style="padding:0 0 24px 0;">
          <span style="display:inline-block; background-color:#FFE9E2; color:#7E2B00; font-family:'JetBrains Mono', Consolas, monospace; font-size:13px; font-weight:500; padding:6px 14px; border-radius:9999px; border:1px solid #DEC0B6;">
            Brier: 0.18
          </span>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
          على 18 شهرا من التنبؤات التاريخية — معايرة قابلة للتحقق، أعلى من وسيط أسواق التنبؤ، وأعلى بكثير من خط أساس إجماع المحللين.
        </td></tr>
        <tr><td align="right" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/methodology?ref=apollo-s3e1" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
            تحميل تقرير المنهجية
          </a>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">— أمين، بصيرة</td></tr>
        <tr><td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
          بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
          الدار البيضاء · باريس · دبي · لندن · الرياض.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 3 — Email 2 — Follow-up (J5)

### Email 3.2.FR — Follow-up (français)

**Subject** : Ce que change un Brier 0,18 pour vos arbitrages

**Plain text version**

```
{{first_name}},

Pourquoi ce 0,18 importe concrètement pour vos comités :

Un consensus analyst classique tourne autour d'un Brier de 0,30 à 0,35 sur les questions stratégiques (effets binaires : « le deal passe / ne passe pas », « la régulation arrive / n'arrive pas »). À 0,18, on parle d'une réduction d'erreur de prévision de l'ordre de 40 à 50 %.

Sur un comité d'investissement à 200 M€, ça déplace le seuil de décision sans changer votre univers de risque.

L'audit de 12 cas réels (anonymisés) avec leur résultat ex-post est ici : https://bassira.com/calibration/track-record?ref=apollo-s3e2

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Ce que change 0,18</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Pourquoi ce <strong>0,18</strong> importe concrètement pour vos comités :
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Un consensus analyst classique tourne autour d'un Brier de 0,30 à 0,35 sur les questions stratégiques binaires (« le deal passe / ne passe pas », « la régulation arrive / n'arrive pas »). À 0,18, on parle d'une réduction d'erreur de prévision de l'ordre de 40 à 50 %.
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          Sur un comité d'investissement à 200 M€, ça déplace le seuil de décision sans changer votre univers de risque.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/track-record?ref=apollo-s3e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Voir 12 cas avec résultat ex-post
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 3.2.EN — Follow-up (English)

**Subject** : What 0.18 Brier means for your trade-offs

**Plain text version**

```
{{first_name}},

Why this 0.18 matters concretely for your committees:

A classical analyst consensus sits around a Brier of 0.30 to 0.35 on binary strategic calls ("deal closes / doesn't", "regulation hits / doesn't"). At 0.18, you're looking at a 40 to 50% reduction in forecast error.

On a 200 M€ investment committee, that shifts the decision threshold without changing your risk universe.

Audit of 12 real cases (anonymised) with their ex-post outcome here: https://bassira.com/calibration/track-record?ref=apollo-s3e2

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>What 0.18 means</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Why this <strong>0.18</strong> matters concretely for your committees:
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          A classical analyst consensus sits around a Brier of 0.30 to 0.35 on binary strategic calls ("deal closes / doesn't", "regulation hits / doesn't"). At 0.18, you're looking at a 40 to 50% reduction in forecast error.
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          On a 200 M€ investment committee, that shifts the decision threshold without changing your risk universe.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/track-record?ref=apollo-s3e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            See 12 cases with ex-post outcome
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight for MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 3.2.AR — Follow-up (العربية)

**Subject** : ما يعنيه براير 0.18 لمفاضلاتكم

**Plain text version**

```
{{first_name}}،

لماذا تعني درجة 0.18 شيئا ملموسا لمجالسكم :

إجماع المحللين الكلاسيكي يدور حول درجة براير من 0.30 إلى 0.35 في القرارات الاستراتيجية الثنائية ("تتم الصفقة / لا تتم"، "يصدر التشريع / لا يصدر"). عند 0.18، نتحدث عن خفض في خطأ التنبؤ بنسبة 40 إلى 50 %.

في لجنة استثمار بقيمة 200 مليون يورو، هذا يحرّك عتبة القرار دون تغيير محفظة المخاطر.

تدقيق 12 حالة حقيقية (مجهولة الهوية) مع نتائجها اللاحقة: https://bassira.com/calibration/track-record?ref=apollo-s3e2

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ما يعنيه 0.18</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px;">
        <tr><td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F;">بَصِيرَة</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">{{first_name}}،</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          لماذا تعني درجة <strong>0.18</strong> شيئا ملموسا لمجالسكم :
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          إجماع المحللين الكلاسيكي يدور حول درجة براير من 0.30 إلى 0.35 في القرارات الاستراتيجية الثنائية ("تتم الصفقة / لا تتم"، "يصدر التشريع / لا يصدر"). عند 0.18، نتحدث عن خفض في خطأ التنبؤ بنسبة 40 إلى 50 %.
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
          في لجنة استثمار بقيمة 200 مليون يورو، هذا يحرّك عتبة القرار دون تغيير محفظة المخاطر.
        </td></tr>
        <tr><td align="right" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/track-record?ref=apollo-s3e2" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
            الاطلاع على 12 حالة
          </a>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">— أمين، بصيرة</td></tr>
        <tr><td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
          بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 3 — Email 3 — Break-up (J11)

### Email 3.3.FR — Break-up (français)

**Subject** : Une dernière mesure avant de fermer

**Plain text version**

```
{{first_name}},

Pas de réponse — c'est ok. Une seule chose avant que je ferme votre dossier :

Si vous deviez auditer la calibration de vos propres prévisions stratégiques sur les 18 derniers mois, vous auriez quel Brier ?

C'est une question honnête, pas rhétorique. Si vous voulez le calculer (gratuit, 30 min), le widget est là : https://bassira.com/calibration/self-audit?ref=apollo-s3e3-breakup

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Une dernière mesure</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          Pas de réponse — c'est ok. Une seule chose avant que je ferme votre dossier :
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:18px; line-height:1.6; color:#241915; padding-bottom:24px; font-style:italic;">
          Si vous deviez auditer la calibration de vos propres prévisions stratégiques sur les 18 derniers mois, vous auriez quel Brier ?
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          C'est une question honnête, pas rhétorique. Si vous voulez le calculer (gratuit, 30 minutes), le widget est ouvert.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/self-audit?ref=apollo-s3e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Auditer mon propre Brier
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight pour MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Se désinscrire</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 3.3.EN — Break-up (English)

**Subject** : One final measurement before I close

**Plain text version**

```
{{first_name}},

No reply — fine. One thing before I close the file:

If you had to audit the calibration of your own strategic forecasts over the last 18 months, what Brier would you score?

Honest question, not rhetorical. If you'd like to compute it (free, 30 minutes), the widget is open: https://bassira.com/calibration/self-audit?ref=apollo-s3e3-breakup

— Amine, Bassira
```

**HTML version (inline CSS)**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Final measurement</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
        <tr><td style="padding-bottom:24px; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-weight:700; font-size:20px; color:#A13F0F; letter-spacing:0.08em; text-transform:uppercase;">Bassira</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">{{first_name}},</td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:16px;">
          No reply — fine. One thing before I close the file:
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:18px; line-height:1.6; color:#241915; padding-bottom:24px; font-style:italic;">
          If you had to audit the calibration of your own strategic forecasts over the last 18 months, what Brier would you score?
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:24px;">
          Honest question, not rhetorical. If you'd like to compute it (free, 30 minutes), the widget is open.
        </td></tr>
        <tr><td align="left" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/self-audit?ref=apollo-s3e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Outfit', system-ui, Helvetica, Arial, sans-serif; font-size:15px; font-weight:600; text-decoration:none; padding:12px 24px; border-radius:12px;">
            Audit my own Brier
          </a>
        </td></tr>
        <tr><td style="font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:16px; line-height:1.6; color:#241915; padding-bottom:32px;">— Amine, Bassira</td></tr>
        <tr><td style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Manrope', system-ui, Helvetica, Arial, sans-serif; font-size:12px; line-height:1.5; color:#8A7269;">
          Bassira — Strategic Foresight for MENA &amp; Europe.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">Unsubscribe</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

### Email 3.3.AR — Break-up (العربية)

**Subject** : قياس أخير قبل الإغلاق

**Plain text version**

```
{{first_name}}،

لم يصلني رد — لا بأس. شيء واحد قبل أن أغلق الملف :

إذا كان عليكم تدقيق معايرة تنبؤاتكم الاستراتيجية الخاصة على الأشهر الثمانية عشر الماضية، ما درجة براير التي ستحصلون عليها ؟

سؤال صادق، لا بلاغي. إذا أردتم احتسابها (مجانا، 30 دقيقة)، الأداة مفتوحة: https://bassira.com/calibration/self-audit?ref=apollo-s3e3-breakup

— أمين، بصيرة
```

**HTML version (inline CSS, RTL)**

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>قياس أخير</title></head>
<body style="margin:0; padding:0; background-color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="background-color:#FAF7F2;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="max-width:600px;">
        <tr><td align="right" style="padding-bottom:24px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-weight:700; font-size:22px; color:#A13F0F;">بَصِيرَة</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">{{first_name}}،</td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:16px;">
          لم يصلني رد — لا بأس. شيء واحد قبل أن أغلق الملف :
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:20px; line-height:1.8; color:#241915; padding-bottom:24px; font-style:italic;">
          إذا كان عليكم تدقيق معايرة تنبؤاتكم الاستراتيجية الخاصة على الأشهر الثمانية عشر الماضية، ما درجة براير التي ستحصلون عليها ؟
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:24px;">
          سؤال صادق، لا بلاغي. إذا أردتم احتسابها (مجانا، 30 دقيقة)، الأداة مفتوحة.
        </td></tr>
        <tr><td align="right" style="padding-bottom:32px;">
          <a href="https://bassira.com/calibration/self-audit?ref=apollo-s3e3-breakup" style="display:inline-block; background-color:#A13F0F; color:#FAF7F2; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:12px 24px; border-radius:12px;">
            تدقيق براير الخاصة بي
          </a>
        </td></tr>
        <tr><td align="right" style="font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:18px; line-height:1.8; color:#241915; padding-bottom:32px;">— أمين، بصيرة</td></tr>
        <tr><td align="right" style="border-top:1px solid #DEC0B6; padding-top:16px; font-family:'Tajawal', Helvetica, Arial, sans-serif; font-size:13px; line-height:1.6; color:#8A7269;">
          بصيرة — استشراف استراتيجي لمنطقة الشرق الأوسط وأوروبا.<br>
          <a href="https://bassira.com/unsubscribe?contact={{contact_id}}" style="color:#8A7269; text-decoration:underline;">إلغاء الاشتراك</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

---

## SEQUENCE 3 — LinkedIn DMs

### LinkedIn DM 1 — Court (≤ 500 caractères)

```
Bonjour {{first_name}},

Petite curiosité technique : la plupart des modèles de prévision stratégique ne sont jamais audités. Le nôtre l'est — Brier 0,18 sur 18 mois, bien au-dessus du consensus analyst (0,30-0,35).

Le rapport méthodo est public si ça vous intéresse. Pas un pitch, juste de la donnée vérifiable.

— Amine, Bassira
```

(385 caractères)

### LinkedIn DM 2 — Long (≤ 1300 caractères)

```
Bonjour {{first_name}},

Vu votre rôle de {{title}} chez {{company_name}}, je me permets une question technique : à quand remonte la dernière fois que la calibration de vos prévisions stratégiques internes a été mesurée ex-post ?

La plupart des modèles ne le sont jamais. Le nôtre l'est, et publiquement : notre Brier score actuel est de 0,18 sur 18 mois de prévisions historiques. Pour mémoire, un consensus analyst classique tourne autour de 0,30-0,35 sur les questions binaires (deal passe / ne passe pas, régulation arrive / n'arrive pas). À 0,18, on parle d'une réduction d'erreur de prévision de 40 à 50 %.

Concrètement, sur un comité d'investissement à 200 M€, ça déplace le seuil de décision sans changer le risk universe.

Deux ressources qui peuvent vous être utiles :
1. Le rapport méthodo complet (jeu de test, validation, limites).
2. L'audit de 12 cas réels anonymisés avec leur résultat ex-post.

Je peux vous envoyer les deux. Si en plus vous voulez auditer la calibration de vos propres prévisions internes, on a un widget gratuit (30 min). Pas d'agenda commercial derrière, juste de la donnée vérifiable.

— Amine, Bassira
```

(1294 caractères)

---

# Annexe — Variables Apollo & QA checklist

## Variables Apollo recommandées

| Variable | Description | Fallback |
|----------|-------------|----------|
| `{{first_name}}` | Prénom du prospect | « bonjour » (si vide) |
| `{{last_name}}` | Nom de famille | — |
| `{{title}}` | Fonction | « votre comité » |
| `{{company_name}}` | Société | « votre organisation » |
| `{{trigger_event}}` | Événement déclencheur (Sequence 1) | « cette opération stratégique » |
| `{{recent_sector_event}}` | Choc sectoriel (Sequence 2) | « les dernières turbulences » |
| `{{contact_id}}` | ID Apollo (unsubscribe) | obligatoire |

## QA checklist avant envoi

- [ ] Aucun mot interdit : `AI-powered`, `cutting-edge`, `leverages`, `revolutionary`, `disruptive`, `game-changer`, `synergies`.
- [ ] Aucun emoji.
- [ ] Subject ≤ 60 caractères (mobile preview).
- [ ] Plain-text version ≤ 6 phrases utiles.
- [ ] HTML inline CSS (zéro `<style>` block).
- [ ] CTA = un seul bouton, terracotta `#A13F0F`.
- [ ] Footer Manrope 12 px `#8A7269` + lien unsubscribe.
- [ ] Versions arabes : `dir="rtl"` + `align="right"` + Tajawal.
- [ ] Liens UTM tracés (`?ref=apollo-sXeY`).
- [ ] Signature : « — Amine, Bassira ».
- [ ] Test rendu Outlook 2019, Gmail web, Apple Mail, Apollo preview.

## Cadence Apollo recommandée

| Étape | Sequence 1 | Sequence 2 | Sequence 3 |
|-------|------------|------------|------------|
| Step 1 | J0 — Email cold | J0 — Email cold | J0 — Email cold |
| Step 2 | J3 — Email follow-up | J4 — Email follow-up | J5 — Email follow-up |
| Step 3 | J3 — LinkedIn DM court | J4 — LinkedIn DM court | J5 — LinkedIn DM court |
| Step 4 | J7 — Email break-up | J9 — Email break-up | J11 — Email break-up |
| Step 5 (opt.) | J10 — LinkedIn DM long | J14 — LinkedIn DM long | J18 — LinkedIn DM long |

## Notes A/B testing

- **Subject lines** : tester variantes courtes vs longues (6-9 mots vs 10-13 mots).
- **CTA labels** : `Consulter le stress-test` vs `Voir le rapport` vs `Lancer une simulation`.
- **Hook scénarios** : tester nombre `10 000 agents` vs `simulation multi-agents`.
- **Signature** : tester avec / sans bandeau « Casablanca · Paris · Dubaï · Londres · Riyad ».

---

*Fin du document. Pour mise à jour palette/typo, voir `bassira_causse_brand_guidelines.md`. Pour designs Stitch source, voir dossiers `apollo_outreach_s_quence_{1,2,3}_email/code.html`.*
