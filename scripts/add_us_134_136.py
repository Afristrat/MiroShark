"""Add US-134/135/136 corrective fixes to PRD post-audit."""
import json
from pathlib import Path

p = Path('.ralph/prd.json')
data = json.loads(p.read_text(encoding='utf-8'))

new = [
    {
        "id": "US-134",
        "chantier": "AI-pdf-fixes-loader",
        "title": "Loader fixes : outline.title/summary, outcome.verdict/recommendations, posts, articles, profils complets",
        "description": "Le rapport bassira-sim_ea0eb65b.md revele que le Loader ne remplit pas correctement plusieurs champs critiques : outline.title vide, outcome.verdict non lu, recommendations vides, posts critiques 10 lignes vides, articles generes placeholder casse, profils agents archetype/plateforme vides, current_round/total_rounds=0 alors que sim a fait 19+ rounds, sources documentaires non extraites.",
        "acceptanceCriteria": [
            "outline.title et outline.summary correctement charges depuis outline.json",
            "outcome.verdict, outcome.bullish_pct/bearish_pct, outcome.recommendations (List[str]) extraits depuis outcome.json",
            "config.title (= simulation_requirement) charge pour la question strategique",
            "config.sources extraites depuis simulation_config.json (cles url_docs/urls/documents/files/seed_documents)",
            "state.current_round et state.total_rounds remplis depuis state.json (pas 0 par defaut)",
            "AgentProfile.archetype + .platform + .stance remplis depuis profiles.json/agent_profiles.json/reddit_profiles.json",
            "Posts critiques : extraire au moins 5-10 posts depuis actions.jsonl (action=post/comment/tweet) avec round, agent, content, score",
            "Articles : extraire correctement depuis generated_article.json en List[GeneratedArticle] avec title, body, round, platform, stance",
            "Tests pytest backend/tests/test_loader_completeness.py verifiant fixture sim_aabbcc112233 charge tous ces champs non-None",
            "Test sur sim reelle si dispo (sim_ea0eb65b2e5b skip si absente) : tous les champs remplis"
        ],
        "passes": False,
        "dependencies": ["US-118", "US-119"],
        "metadata": {
            "estimated_hours": 3,
            "priority": "P0",
            "files_to_modify": ["backend/app/services/report_pdf/loader.py"],
            "files_to_create": ["backend/tests/test_loader_completeness.py"],
            "rationale": "Sans loader complet, Enricher et Templates produisent des outputs vides. Trou identifie par audit du rapport genere."
        }
    },
    {
        "id": "US-135",
        "chantier": "AI-pdf-fixes-enricher",
        "title": "Enricher fixes : KPI Hero reel, pivotal_moments, sanitize LLM (filtrer tool_call), takeaways reels",
        "description": "Audit revele: KPI Hero affiche 0.0 % confiance + Brier 0.0 (valeurs default), aucun pivotal_moment detecte, et CRITIQUE : section Synthesis & Implications contient un tool_call insight_forge brut LLM injecte tel quel dans le livrable client (DEFCON 1 - donnee non rendue). Enricher doit calculer KPI reel + detecter pivotal_moments + sanitize toute sortie LLM avant injection.",
        "acceptanceCriteria": [
            "KPIHero.confidence_pct calcule depuis outcome.bullish_pct/bearish_pct (pas hardcoded 0.0)",
            "KPIHero.brier_score lu depuis quality.brier_score (pas 0.0 par defaut)",
            "KPIHero.verdict copie depuis outcome.verdict",
            "KPIHero.scenarios_distribution depuis outcome metrics si disponible",
            "pivotal_moments detectes en scannant trajectory.rounds avec seuil delta_score > 0.20 entre 2 rounds consecutifs",
            "CRITIQUE : sanitize_llm_output(text) supprime tout <tool_call>...</tool_call>, <function_call>...</function_call>, <thinking>...</thinking> avant injection dans context.interpretations[chart] ou executive_takeaways",
            "executive_takeaways : si deja presents dans outline (3 bullets), les utiliser ; sinon generer 3 via LLM avec sanitize sortie",
            "Tests pytest backend/tests/test_enricher_sanitize.py : input avec tool_call -> output sans, KPI Hero non-zero sur fixture",
            "Test contexte avec outcome.recommendations vide -> executive_takeaways quand meme generes depuis outline.summary"
        ],
        "passes": False,
        "dependencies": ["US-118", "US-124"],
        "metadata": {
            "estimated_hours": 3,
            "priority": "P0",
            "files_to_modify": ["backend/app/services/report_pdf/enricher.py"],
            "files_to_create": ["backend/tests/test_enricher_sanitize.py"],
            "rationale": "DEFCON 1: tool_call brut LLM injecte dans livrable client. Sanitize obligatoire."
        }
    },
    {
        "id": "US-136",
        "chantier": "AI-pdf-fixes-templates",
        "title": "Templates fixes : numerotation sections 1-N, format dates Babel FR, embed charts data URI, articles non vides",
        "description": "Audit revele bugs templates Jinja2: tableau Sections detaillees toutes numerotees 1, date generated_at brute ISO au lieu de format FR humain, charts referencent fichiers inexistants dans .md, Article genere placeholder vide.",
        "acceptanceCriteria": [
            "Tableau Sections detaillees numerote 1,2,3,4,...,N (utiliser loop.index Jinja2)",
            "Filter Jinja2 |format_date qui formate ISO datetime -> '6 mai 2026 a 15h07 UTC' (FR), 'May 6, 2026 at 3:07 PM UTC' (EN), equivalent AR via babel ou strftime locale-aware",
            "Charts embed : MdRenderer genere le markdown avec ![alt](data:image/png;base64,XXXX) en encodant les bytes PNG du ChartFactory ; HTML->PDF reuse ces data URI",
            "Article template : si generated_articles vide, afficher callout warning info au lieu de placeholder casse",
            "Article template : si non-vide, afficher title + body + round + platform + stance correctement formate",
            "Posts critiques table : si actions vides, afficher callout au lieu de 10 lignes vides",
            "Profils agents annexe 7.2 : afficher uniquement les colonnes avec data reelle (skip Archetype/Plateforme si tous vides)",
            "Tests pytest backend/tests/test_templates_render_quality.py : numerotation OK, dates formatees, charts data URI present, fallbacks gracieux"
        ],
        "passes": False,
        "dependencies": ["US-123", "US-118"],
        "metadata": {
            "estimated_hours": 4,
            "priority": "P0",
            "files_to_modify": [
                "backend/app/templates/pdf_report/_full.md.j2",
                "backend/app/templates/pdf_report/02_toc.md.j2",
                "backend/app/templates/pdf_report/04_dynamic.md.j2",
                "backend/app/templates/pdf_report/05_verdict.md.j2",
                "backend/app/templates/pdf_report/07_appendix.md.j2",
                "backend/app/services/report_pdf/jinja_env.py",
                "backend/app/services/report_pdf/renderer.py"
            ],
            "files_to_create": ["backend/tests/test_templates_render_quality.py"],
            "rationale": "Numerotation cassee + dates brutes + charts non embarques + articles placeholder. Tous identifies par audit Amine."
        }
    }
]

data['stories'].extend(new)
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('Added US-134/135/136. passes:false count:', sum(1 for s in data['stories'] if not s['passes']))
