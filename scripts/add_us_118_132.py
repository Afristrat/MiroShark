"""Add US-118 to US-132 to .ralph/prd.json — PDF report refactor."""
import json
from pathlib import Path

p = Path('.ralph/prd.json')
data = json.loads(p.read_text(encoding='utf-8'))


def story(sid, chantier, title, description, ac, deps, priority, hours,
          files_create=None, files_modify=None, **extra):
    s = {
        "id": sid,
        "chantier": chantier,
        "title": title,
        "description": description,
        "acceptanceCriteria": ac,
        "passes": False,
        "dependencies": deps,
        "metadata": {
            "estimated_hours": hours,
            "priority": priority,
        }
    }
    if files_create:
        s["metadata"]["files_to_create"] = files_create
    if files_modify:
        s["metadata"]["files_to_modify"] = files_modify
    for k, v in extra.items():
        s["metadata"][k] = v
    return s


new_stories = [
    story(
        "US-118", "U-pdf-foundations",
        "Schema PDFReportContext exhaustif (Pydantic)",
        "Crée un schema Pydantic v2 mappant les 20+ artifacts simulation + report markdown dans un objet PDFReportContext typé. Sub-models : SimConfig, SimState, Outcome, QualityMetrics, Trajectory, AgentProfile, SocialNetwork, Demographics, Counterfactual, DirectorEvent, GeneratedArticle, AgentInterview, Outline, KPIHero, PivotalMoment. Tous champs optionnels avec default explicite. Field validators sur lang in {fr,en,ar}, framework in {cerberus,market,crisis,policy,decision}. Tests pytest valid + invalid construction.",
        [
            "backend/app/services/report_pdf/schema.py créé avec PDFReportContext Pydantic v2",
            "Sub-models typés pour les 20+ artifacts (voir description)",
            "Tous les champs optionnels ont default explicite (None ou []), aucun Any injustifié",
            "Field validators : lang enum, framework enum, report_id regex",
            "tests/test_pdf_context_schema.py : valid construction depuis dict réaliste + invalid raises ValidationError",
            "Documentation inline avec docstring listant sub-fields et leur source artifact"
        ],
        [], "P0", 3,
        files_create=[
            "backend/app/services/report_pdf/__init__.py",
            "backend/app/services/report_pdf/schema.py",
            "backend/tests/test_pdf_context_schema.py"
        ]
    ),
    story(
        "US-119", "U-pdf-foundations",
        "Loader complet (charge tous les artifacts simulation + report)",
        "Service PDFContextLoader qui charge les 20+ artifacts depuis simulation_dir + report_folder dans un PDFReportContext. Gestion graceful des fichiers manquants (warning, sub-field None). Si fichier obligatoire absent (outline.json, simulation_config.json) : raise PDFContextLoaderError. Tests sur sim_ea0eb65b2e5b réelle.",
        [
            "backend/app/services/report_pdf/loader.py avec PDFContextLoader.load(simulation_id, report_id, lang) -> PDFReportContext",
            "Charge tous les fichiers : simulation_config.json, state.json, outcome.json, quality.json, trajectory.json, agent_profiles.json, reddit/twitter/polymarket profiles, network.json, demographics.json, counterfactual_injection.json, generated_article.json, actions.jsonl, events.jsonl, outline.json, full_report.md, sections section_NN.md, agent_log.jsonl",
            "Fichier optionnel manquant : warning logger + sub-field None, pas de crash",
            "Fichier obligatoire manquant : raise PDFContextLoaderError avec message explicite",
            "Test sur sim réelle : tous les sous-fields présents",
            "Tests unitaires : missing files, malformed JSON, edge cases vides"
        ],
        ["US-118"], "P0", 4,
        files_create=[
            "backend/app/services/report_pdf/loader.py",
            "backend/tests/test_pdf_context_loader.py"
        ]
    ),
    story(
        "US-120", "U-pdf-foundations",
        "Migration pdf_branding Supabase + page admin CRUD avec preview live",
        "Permet aux super-admin et org admin de configurer le branding PDF (logo, header, footer, palette, fonts, disclaimer) via UI Coolify-like avec versioning et preview live. Multi-tenant white-label ready. Whitelist de placeholders {{logo}} {{section}} {{page}} etc. RLS strict.",
        [
            "Migration supabase/migrations/20260506_001_pdf_branding.sql idempotente",
            "Table pdf_branding avec colonnes : id uuid, org_id uuid FK, name, logo_url, header_left/right, footer_left/center/right, palette_primary/secondary, font_titles/body/mono, disclaimer_text jsonb (multilang), valid_from/to, created_by, created_at",
            "RLS : super-admin bypass, org admin CRUD on org_id in user_orgs(), members read-only",
            "Index (org_id, valid_from desc) pour récupérer branding actif",
            "Helper backend/app/services/pdf_branding.py : get_active_branding, create_branding, list_branding, update_branding",
            "Endpoints GET/POST/PATCH /api/admin/branding + POST /api/admin/branding/<id>/preview qui renvoie PNG aperçu",
            "Frontend AdminBrandingView.vue route /admin/branding avec form + preview live",
            "Validation placeholders whitelist (sanitization XSS server-side)",
            "Tests pytest RLS scenarios + helpers + preview endpoint",
            "Tests Playwright form fonctionne + preview se met à jour"
        ],
        ["US-091"], "P0", 6,
        files_create=[
            "supabase/migrations/20260506_001_pdf_branding.sql",
            "backend/app/services/pdf_branding.py",
            "backend/app/api/admin_branding.py",
            "frontend/src/views/AdminBrandingView.vue",
            "backend/tests/test_pdf_branding.py",
            "frontend/tests/e2e/admin-branding.spec.ts"
        ]
    ),
    story(
        "US-121", "V-pdf-i18n",
        "TextNormalizer FR/EN/AR + LanguageTool self-host",
        "Service TextNormalizer par langue applique règles typographiques (FR accents majuscules DEFCON 1, espaces insécables fines U+202F, guillemets francais, apostrophe typographique, em-dash, ligatures, format nombres ; EN pas d'espaces avant ponctuation, guillemets typographiques ; AR ponctuation arabe, chiffres hindi optionnels, dir=rtl, fallback Tajawal). Container LanguageTool Docker self-host pour spell/grammar check.",
        [
            "backend/app/services/text_normalizer/__init__.py avec TextNormalizer(lang).normalize(text) -> NormalizedText",
            "fr.py : espaces insécables fines avant : ; ! ? % EUR, guillemets francais, apostrophe typographique, accents majuscules forcés (dictionnaire ETAT, A, ETRE...), em-dash, ligatures, format nombres",
            "en.py : pas d'espaces avant ponctuation, guillemets typographiques, em-dash style choisi",
            "ar.py : ponctuation arabe (virgule arabe, point-virgule arabe, point d'interrogation arabe), chiffres hindi optionnels, force dir=rtl si HTML, fallback Tajawal",
            "docker-compose.languagetool.yml ajoute container meyay/languagetool sur port interne 8010 avec healthcheck",
            "languagetool_client.py : POST /v2/check, parse réponse, retourne List[Issue]",
            "Mode strictness strict|standard|permissive configurable",
            "Tests pytest 30+ cas par langue (avant/après normalisation, edge cases)",
            "CI hook pre-commit qui lint tous les .md.j2 et fail si typo cassée"
        ],
        [], "P0", 6,
        files_create=[
            "backend/app/services/text_normalizer/__init__.py",
            "backend/app/services/text_normalizer/fr.py",
            "backend/app/services/text_normalizer/en.py",
            "backend/app/services/text_normalizer/ar.py",
            "backend/app/services/text_normalizer/languagetool_client.py",
            "backend/tests/test_text_normalizer_fr.py",
            "backend/tests/test_text_normalizer_en.py",
            "backend/tests/test_text_normalizer_ar.py",
            "docker-compose.languagetool.yml",
            ".pre-commit-hooks/check_typography.py"
        ]
    ),
    story(
        "US-122", "W-pdf-charts",
        "ChartFactory matplotlib server-side palette Causse (5 charts signature)",
        "Service ChartFactory génère 5 charts PNG 300 DPI avec palette Causse Warm Intelligence : belief_drift, polymarket_curves, demographic_pyramid, influence_leaderboard, interaction_network. Si données absentes, retourne PNG placeholder élégant. Tests visual regression via pytest-mpl.",
        [
            "backend/app/services/report_pdf/charts.py avec ChartFactory(context).belief_drift/polymarket_curves/demographic_pyramid/influence_leaderboard/interaction_network",
            "Chaque méthode retourne bytes PNG 300 DPI dimensionné A4 content width",
            "Style matplotlib custom rcParams snapshot dans charts/_style.py : couleurs --wi-orange/mint/cream/charcoal/terra, polices Outfit titres + Manrope axes",
            "belief_drift : line chart, X=rounds, Y=beliefs, ligne par agent archétypal, callouts pivotal_moments",
            "polymarket_curves : multiple market probability curves over time",
            "demographic_pyramid : pyramide horizontale gauche/droite par genre/segment",
            "influence_leaderboard : bar chart horizontal top-10 avec scores",
            "interaction_network : networkx layout spring/kamada-kawai, color by archetype, size by influence",
            "Données absentes → PNG placeholder élégant",
            "Tests pytest fixture + visual regression pytest-mpl tolérance pixel"
        ],
        ["US-118", "US-119"], "P0", 5,
        files_create=[
            "backend/app/services/report_pdf/charts.py",
            "backend/app/services/report_pdf/_style.py",
            "backend/tests/test_charts.py"
        ]
    ),
    story(
        "US-123", "X-pdf-templates",
        "Templates Jinja2 Markdown source unique + macros réutilisables",
        "Templates Markdown Jinja2 (.md.j2) source unique pour toutes les sections du rapport + macros (KPI card, callout, pull quote, table, chart-with-narrative). Front-matter YAML obligatoire. Tous textes passent par TextNormalizer via filter Jinja2. Section Dynamic intègre charts narrativés. Section Appendix inclut full_report.md content si présent.",
        [
            "Dossier backend/app/templates/pdf_report/ avec : 00_cover.md.j2, 01_exec_summary.md.j2, 02_toc.md.j2, 03_diagnostic.md.j2, 04_dynamic.md.j2, 05_verdict.md.j2, 06_recommendations.md.j2, 07_appendix.md.j2, _full.md.j2 (assembleur)",
            "Front-matter YAML obligatoire dans _full.md.j2 : title, report_id, simulation_id, lang, framework, generated_at, template_version, branding_version",
            "_macros.md.j2 avec : kpi_card, callout (info/warning/critical), pull_quote, table_from_data, chart_with_narrative",
            "Tous templates passent par TextNormalizer lang-aware avant rendu (filter normalize)",
            "Section 04 inclut belief_drift + polymarket + influencers narrativés via chart_with_narrative",
            "Section 07 inclut full_report.md content si présent",
            "Tests : génère MD pour chaque section sur fixture, vérifie présence sections + respect typographique"
        ],
        ["US-118", "US-121", "US-122"], "P0", 5,
        files_create=[
            "backend/app/templates/pdf_report/00_cover.md.j2",
            "backend/app/templates/pdf_report/01_exec_summary.md.j2",
            "backend/app/templates/pdf_report/02_toc.md.j2",
            "backend/app/templates/pdf_report/03_diagnostic.md.j2",
            "backend/app/templates/pdf_report/04_dynamic.md.j2",
            "backend/app/templates/pdf_report/05_verdict.md.j2",
            "backend/app/templates/pdf_report/06_recommendations.md.j2",
            "backend/app/templates/pdf_report/07_appendix.md.j2",
            "backend/app/templates/pdf_report/_full.md.j2",
            "backend/app/templates/pdf_report/_macros.md.j2",
            "backend/tests/test_md_templates.py"
        ]
    ),
    story(
        "US-124", "Y-pdf-enrich",
        "Enricher LLM (insights, pivotal_moments, interpretations narratives par chart)",
        "Service Enricher transforme données brutes en insights C-level via short LLM calls : compute KPI hero, detect pivotal moments dans trajectory, generate chart narratives (~80 mots par chart, prompt strict, cache LRU), extract executive takeaways. Tous textes passent par TextNormalizer avant injection.",
        [
            "backend/app/services/report_pdf/enricher.py avec Enricher(context).enrich() -> PDFReportContext",
            "_compute_kpi_hero : KPIHero (verdict + confidence_pct + Brier live + scenario distribution)",
            "_detect_pivotal_moments : scan trajectory, détecte changements brusques influence/belief, retourne List[PivotalMoment(round, agent, event, delta_score)]",
            "_generate_chart_narratives : pour chaque chart, narrative ~80 mots via LLM court (Claude Haiku ou Moonshot kimi-k2-turbo) avec prompt strict ; cache LRU (chart_id, data_hash, lang) TTL 24h",
            "_extract_executive_takeaways : 3 takeaways prioritaires C-level depuis outline + outcome + pivotal_moments",
            "_pass_through_normalizer : tous textes générés passent par TextNormalizer(lang)",
            "Tests pytest fixture : kpi_hero rempli, pivotal_moments triés par round, interpretations présentes, takeaways non vides",
            "Mock LLM calls avec unittest.mock pour tests déterministes"
        ],
        ["US-118", "US-121", "US-122"], "P0", 5,
        files_create=[
            "backend/app/services/report_pdf/enricher.py",
            "backend/tests/test_enricher.py"
        ]
    ),
    story(
        "US-125", "Z-pdf-renderer",
        "Renderer pipeline (MD direct + PDF via WeasyPrint + brand CSS injectable)",
        "Service Renderer prend PDFReportContext + branding row, produit .md (GFM avec front-matter) et .pdf (markdown-it -> HTML -> WeasyPrint). CSS @page natif pour headers/footers running elements. Cover page sans header/footer via @page :first. TOC auto via target-counter. Embed fonts woff2 via @font-face. PDF metadata set. Multilang FR/EN/AR.",
        [
            "backend/app/services/report_pdf/renderer.py avec Renderer(context, branding).render_md() -> str et .render_pdf() -> bytes",
            "render_md : assemble templates _full.md.j2 + sections + macros, output GFM string avec front-matter YAML",
            "render_pdf : render_md → markdown-it-py → HTML → inject pdf_brand.css avec variables branding → embed charts PNG base64 → embed fonts @font-face → WeasyPrint write_pdf",
            "Headers/footers via CSS @page natif WeasyPrint avec running elements (logo, section, page)",
            "Cover page : @page :first sans header/footer",
            "TOC auto via target-counter() CSS",
            "PDF metadata set (title, author=Bassira, keywords, lang) via Document.metadata",
            "Tests pytest fixture : produit MD valid GFM, produit PDF valid (pypdf nb pages > 5, metadata présentes)",
            "Test multilang : génère FR + EN + AR sur même fixture, vérifie polices et direction"
        ],
        ["US-118", "US-119", "US-120", "US-122", "US-123", "US-124"], "P0", 7,
        files_create=[
            "backend/app/services/report_pdf/renderer.py",
            "backend/app/templates/pdf_report/pdf_brand.css.j2",
            "backend/static/fonts/.gitkeep",
            "backend/tests/test_renderer.py"
        ]
    ),
    story(
        "US-126", "AA-pdf-workflow",
        "Workflow états 7 transitions + audit log immuable",
        "Lifecycle 7 états (GENERATING -> DRAFT -> IN_REVIEW -> PENDING_APPROVAL -> APPROVED -> DELIVERED -> ARCHIVED) avec audit log immuable insert-only. Locking optimiste sur IN_REVIEW. Validation transitions légales.",
        [
            "Migration supabase/migrations/20260506_002_report_workflow.sql idempotente",
            "Table report_states : report_id PK, state enum, current_version, last_transition_at, last_transition_by, locked_by null, locked_at null",
            "Table report_audit_log : id, report_id, from_state, to_state, actor_id, actor_email, ip_address, user_agent, snapshot_hash, comment, created_at",
            "RLS : insert-only audit_log, super-admin SELECT all, member SELECT own org",
            "Index (report_id, created_at desc) sur audit_log",
            "Helper report_workflow.py : transition(report_id, to_state, actor, comment) avec validation transitions légales",
            "Endpoints GET /api/admin/reports/<id>/state + POST /api/admin/reports/<id>/transition",
            "Locking optimiste IN_REVIEW (lock_by + lock_at) ; auto-release 30 min inactivité",
            "Tests pytest : transitions légales/illégales, audit immutability (UPDATE bloqué par RLS), lock acquisition/release/timeout"
        ],
        ["US-091"], "P0", 4,
        files_create=[
            "supabase/migrations/20260506_002_report_workflow.sql",
            "backend/app/services/report_workflow.py",
            "backend/app/api/admin_reports.py",
            "backend/tests/test_report_workflow.py"
        ]
    ),
    story(
        "US-127", "AB-pdf-review-ui",
        "Page admin /admin/reports/<id>/review (split view PDF + Tiptap + CodeMirror + LLM rephrase + diff)",
        "UI super-admin split-view : PDF preview (PDF.js) à gauche, tree sections + editor à droite. Tiptap rich-text inline avec validation typo live. CodeMirror raw MD editor. Bouton Rephrase with AI réutilisant /api/report/chat. Diff visuel inline entre versions (diff-match-patch). Système commentaires margin notes.",
        [
            "frontend/src/views/AdminReportReviewView.vue route /admin/reports/:id/review",
            "Layout split 50/50 PDF.js iframe + tree+editor",
            "PDF preview rafraîchi automatiquement après save (debounce 2s)",
            "Tree affiche outline.json avec indicators issues count typo",
            "Click paragraphe → éditeur Tiptap inline avec toolbar (bold, italic, link, blockquote) + validation typo live",
            "Toggle Edit raw markdown ouvre CodeMirror 6 syntax highlighting GFM",
            "Bouton Rephrase with AI panneau avec prompts rapides (Plus formel, C-level, Raccourcir 30%, Custom) → call /api/report/chat → diff suggéré → accept/reject",
            "Bouton Compare versions diff visuel inline (diff-match-patch) avec couleurs rouge/vert/jaune et auteur par ligne",
            "Système commentaires margin notes : sélection texte → emoji bulle → stocké report_comments DB",
            "Migration 20260506_003_report_versions.sql : tables report_versions + report_comments",
            "Endpoints GET/POST /api/admin/reports/<id>/versions",
            "Tests Playwright : ouvre page, edit Tiptap, save, vérifie new version + diff visible"
        ],
        ["US-126", "US-111"], "P0", 10,
        files_create=[
            "frontend/src/views/AdminReportReviewView.vue",
            "frontend/src/components/AdminReportTree.vue",
            "frontend/src/components/TiptapEditor.vue",
            "frontend/src/components/RawMdEditor.vue",
            "frontend/src/components/VersionDiff.vue",
            "supabase/migrations/20260506_003_report_versions.sql",
            "backend/app/api/admin_report_versions.py",
            "backend/tests/test_report_versions.py",
            "frontend/tests/e2e/admin-report-review.spec.ts"
        ]
    ),
    story(
        "US-128", "AC-pdf-finalize",
        "Approve & Sign (snapshot immuable + watermark optionnel toggle + signature optionnelle)",
        "Action super-admin Approve & Sign crée snapshot immuable avec SHA256 hash global. Si watermark_recipient fourni : filigrane diagonal pâle sur chaque page contenu. Si sign=true : signature PAdES via pyHanko. Workflow auto APPROVED -> DELIVERED après envoi.",
        [
            "Endpoint POST /api/admin/reports/<id>/approve body {watermark_recipient, sign} (super-admin only)",
            "Snapshot immuable : markdown S3 reports/<id>/snapshots/<version>/full.md, branding JSON, fonts woff2 copiés, charts PNG, SHA256 global stocké dans audit_log.snapshot_hash",
            "Watermark si recipient non null : CSS rotate(-30deg) opacity 0.08 texte recipient + CONFIDENTIEL + NDA sur chaque page contenu (pas cover)",
            "Signature PAdES si sign=true via pyHanko avec cert configuré BASSIRA_SIGNING_CERT_P12_PATH + PASSWORD env Coolify",
            "Workflow transition automatique APPROVED -> DELIVERED après envoi",
            "Tests pytest : snapshot files créés, hash stable, watermark visible (PDF text extraction), signature valid (selon cert dispo)"
        ],
        ["US-125", "US-126"], "P0", 6,
        files_create=[
            "backend/app/services/report_pdf/snapshot.py",
            "backend/app/services/report_pdf/watermark.py",
            "backend/app/services/report_pdf/signer.py",
            "backend/tests/test_snapshot_watermark.py"
        ]
    ),
    story(
        "US-129", "AD-pdf-async",
        "Génération hybride sync/async (preview 1p sync + full async via queue Redis + webhook)",
        "Endpoints sync preview (cover seul, ≤5s) + async full generation via queue RQ Redis (réutilise coolify-redis). Worker pre-warm fonts WeasyPrint au boot. Cache LRU TTL 24h. Compression Ghostscript -dPDFSETTINGS=/prepress.",
        [
            "Endpoint POST /api/admin/reports/<id>/preview (sync ≤5s) renvoie PDF bytes du cover seul",
            "Endpoint POST /api/admin/reports/<id>/generate body {variant} → enqueue async, retourne {job_id, status_url}",
            "Worker backend/app/workers/pdf_generation_worker.py : consume queue, charge context, enrichit, render, snapshot, store, callback webhook",
            "Queue RQ + Redis (coolify-redis) ; config REDIS_URL env",
            "Endpoint GET /api/admin/reports/<id>/jobs/<job_id> polling status (queued|started|finished|failed) + URL téléchargement si finished",
            "Pre-warm worker : charge fonts WeasyPrint au boot (saves 2-3s/req)",
            "Cache LRU (sim_id, report_id, branding_v, template_v, variant, lang) TTL 24h",
            "Compression Ghostscript -dPDFSETTINGS=/prepress (-50% taille)",
            "Tests pytest : enqueue, mock worker, vérifie webhook callback fired",
            "Tests load 5 jobs parallèles, mesure throughput"
        ],
        ["US-125", "US-128"], "P1", 6,
        files_create=[
            "backend/app/workers/pdf_generation_worker.py",
            "backend/app/api/pdf_generation.py",
            "backend/tests/test_pdf_async.py"
        ]
    ),
    story(
        "US-130", "AE-pdf-delivery",
        "Delivery (URL signée TTL + email Resend + tracking téléchargements avec géo)",
        "Super-admin delivre rapport finalisé via URL signée HMAC SHA256 expirante + email Resend (réutilise email_service.py). Tracking dans report_downloads (timestamp, IP, geo CF-IPCountry, user_agent). Page admin tracking + bouton Re-send fresh link. Auto-archive 90 jours après dernière download.",
        [
            "Endpoint POST /api/admin/reports/<id>/deliver body {recipient_email, recipient_name, expiry_days=7, language=fr} super-admin only",
            "URL signée HMAC SHA256 + expiry timestamp + report_id + recipient_id format /r/<token>",
            "Endpoint GET /r/<token> : valide token, log download dans report_downloads, stream PDF avec content-disposition attachment",
            "Migration 20260506_004_report_delivery.sql : tables report_deliveries + report_downloads",
            "Email Resend template report_delivery.html multilang : preview thumb + lien expirant + disclaimer + signature Bassira",
            "Page admin /admin/reports/<id>/tracking : liste deliveries + downloads par recipient avec géo + bouton Re-send fresh link",
            "Auto-archive ARCHIVED 90 jours après dernière download",
            "Tests pytest : URL signée valid/expired/tampered, download log inserted, re-send invalidates old token",
            "Tests Playwright : page tracking affiche downloads"
        ],
        ["US-128"], "P1", 5,
        files_create=[
            "supabase/migrations/20260506_004_report_delivery.sql",
            "backend/app/services/report_delivery.py",
            "backend/app/api/report_delivery.py",
            "backend/app/templates/emails/report_delivery.html",
            "frontend/src/views/AdminReportTrackingView.vue",
            "backend/tests/test_report_delivery.py",
            "frontend/tests/e2e/admin-report-tracking.spec.ts"
        ]
    ),
    story(
        "US-131", "AF-pdf-variants",
        "4 variantes PDF (exec digest 5p / full 50p / public excerpt 3p / one-pager 1p)",
        "4 variantes du même rapport via template_set selection. Public variant : masquage automatique noms agents/orgs et désactive watermark recipient. One-pager : layout 2 colonnes CSS Grid dense. Cover commune mais titre adapté.",
        [
            "Argument variant accepté dans Renderer + endpoint generate (US-129)",
            "Template sets dans backend/app/templates/pdf_report/<variant>/ : full/ (8 sections complètes), exec/ (cover+exec_summary+verdict+recommendations+appendix court 5p), public/ (cover+3 takeaways anonymisés+1 chart 3p), one-pager/ (A4 unique 6 KPI cards+verdict+3 reco condensées)",
            "Public variant : anonymizer.py masque noms agents/orgs (regex → [Org A], [Agent #1]) et désactive watermark",
            "One-pager : layout 2 colonnes CSS Grid dense",
            "Cover commune titre adapté (Executive Summary / Public Summary / One-Pager / Full Report)",
            "Tests : génère 4 variantes sur même fixture, vérifie nb pages, présence/absence sections clés",
            "Tests visual regression sur 4 variantes en FR/EN"
        ],
        ["US-123", "US-125"], "P1", 6,
        files_create=[
            "backend/app/templates/pdf_report/exec/00_cover.md.j2",
            "backend/app/templates/pdf_report/exec/01_exec_summary.md.j2",
            "backend/app/templates/pdf_report/exec/05_verdict.md.j2",
            "backend/app/templates/pdf_report/exec/06_recommendations.md.j2",
            "backend/app/templates/pdf_report/public/00_cover.md.j2",
            "backend/app/templates/pdf_report/public/01_exec_summary.md.j2",
            "backend/app/templates/pdf_report/one-pager/00_cover.md.j2",
            "backend/app/services/report_pdf/anonymizer.py",
            "backend/tests/test_pdf_variants.py"
        ]
    ),
    story(
        "US-132", "AG-pdf-quality",
        "Tests pipeline E2E + accessibilité PDF/UA + visual regression golden masters",
        "Suite pytest E2E sur 12 PDFs (FR/EN/AR x 4 variants). PDF/UA compliance via veraPDF. Tagged PDF. Alt text sur charts. Contrast linter palette WCAG AA. Visual regression golden masters tolérance pixel 0.5%.",
        [
            "backend/tests/test_pdf_pipeline_e2e.py : génère 12 PDFs (FR/EN/AR x 4 variants), vérifie nb pages plausible, métadonnées set, hash stable",
            "PDF/UA compliance : WeasyPrint --pdf/ua-1 activé en prod, vérifié via veraPDF Java en CI",
            "Tagged PDF : Headings/Paragraphs/Figures/Tables ont rôle PDF correct (pypdf StructParent)",
            "Alt text sur charts : <img alt> non vide propagé en PDF tags",
            "scripts/lint_palette_contrast.py parse pdf_brand.css et vérifie WCAG AA (ratio ≥ 4.5:1 normal, ≥ 3:1 large)",
            "backend/tests/test_pdf_visual_regression.py avec golden masters tolérance pixel 0.5% via pdf2image + Pillow.ImageChops.difference",
            "CI : pytest -m visual_regression",
            "docs/PDF_QUALITY_GATES.md : comment ajouter golden master, debugger régression visuelle"
        ],
        ["US-125", "US-131"], "P1", 5,
        files_create=[
            "backend/tests/test_pdf_pipeline_e2e.py",
            "backend/tests/test_pdf_visual_regression.py",
            "backend/tests/fixtures/pdf_golden/.gitkeep",
            "scripts/lint_palette_contrast.py",
            "docs/PDF_QUALITY_GATES.md"
        ]
    ),
]

data['stories'].extend(new_stories)
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

# Verify
data2 = json.loads(p.read_text(encoding='utf-8'))
total = len(data2['stories'])
passes_false = sum(1 for s in data2['stories'] if not s['passes'])
new_count = len(new_stories)
print(f"Added: {new_count} stories")
print(f"Total stories: {total}")
print(f"passes:false: {passes_false}")
print(f"First new: {new_stories[0]['id']}, Last: {new_stories[-1]['id']}")
