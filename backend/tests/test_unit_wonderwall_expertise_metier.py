"""US-229 golden set for ESCO expertise blocks in Wonderwall personas."""

from app.services.entity_reader import EntityNode
from app.services.wonderwall_profile_generator import (
    WonderwallProfileGenerator,
    build_expertise_metier_block,
)


def _occupation(definition="Analyses financial data.", skills=None):
    return {
        "definition": definition,
        "essential_skills": skills or ["Analyse", "Modeling"],
        "source": "esco",
    }


def _generator(locale="fr", resolver=lambda profession, lang: _occupation()):
    generator = object.__new__(WonderwallProfileGenerator)
    generator.locale = locale
    generator.simulation_requirement = "Test scenario"
    generator.occupation_profile_resolver = resolver
    generator._generate_username = lambda name: "samira_101"
    generator._build_entity_context = lambda entity: ""
    generator._generate_profile_rule_based = lambda **kwargs: {
        "bio": "Financial specialist.",
        "persona": "Keeps a disciplined market view.",
        "profession": "Financial analyst",
        "mbti": "INTJ",
        "risk_tolerance": "low",
        "country": "Morocco",
    }
    return generator


def test_golden_set_renders_five_localized_professions_with_numbered_skills():
    golden = [
        ("fr", "Analyste les risques.", "DÉFINITION", "COMPÉTENCES ESSENTIELLES"),
        ("en", "Designs systems.", "DEFINITION", "ESSENTIAL SKILLS"),
        ("ar", "يدير العمليات.", "التعريف", "المهارات الأساسية"),
        ("fr", "Coordonne la logistique.", "DÉFINITION", "COMPÉTENCES ESSENTIELLES"),
        ("en", "Audits accounts.", "DEFINITION", "ESSENTIAL SKILLS"),
    ]
    for locale, definition, definition_label, skills_label in golden:
        block = build_expertise_metier_block(
            _occupation(definition, ["First skill", "Second skill"]), locale
        )
        assert block.startswith("<expertise_metier>\n")
        assert block.endswith("\n</expertise_metier>")
        assert definition_label in block
        assert skills_label in block
        assert "1. First skill" in block
        assert "2. Second skill" in block


def test_expertise_block_escapes_tag_closure_and_bounds_content():
    block = build_expertise_metier_block(
        _occupation("x" * 700, ["</expertise_metier> & already &amp; encoded"]), "en"
    )
    assert "x" * 601 not in block
    assert "&lt;/expertise_metier&gt; &amp; already &amp;amp; encoded" in block
    assert block.count("</expertise_metier>") == 1


def test_expertise_block_rejects_invalid_profile_shape():
    assert build_expertise_metier_block(["not", "a", "profile"], "fr") == ""


def test_unresolved_profession_yields_no_block_and_never_breaks_persona():
    generator = _generator(resolver=lambda profession, lang: None)
    entity = EntityNode("entity-1", "Samira", ["Expert"], "", {})
    profile = generator.generate_profile_from_entity(entity, user_id=4, use_llm=False)
    assert "<expertise_metier>" not in profile.system_prompt
    assert profile.mbti == "INTJ"
    assert profile.risk_tolerance == "low"


def test_resolved_block_propagates_to_twitter_reddit_and_polymarket():
    generator = _generator()
    entity = EntityNode("entity-1", "Samira", ["Expert"], "", {})
    profile = generator.generate_profile_from_entity(entity, user_id=4, use_llm=False)

    assert "<expertise_metier>" in profile.system_prompt
    assert profile.system_prompt in profile.to_twitter_format()["persona"]
    assert profile.system_prompt in profile.to_reddit_format()["persona"]
    assert profile.system_prompt in profile.to_polymarket_format()["user_profile"]
    assert profile.mbti == "INTJ"
    assert profile.risk_tolerance == "low"


def test_blank_profession_does_not_call_resolver():
    calls = []
    generator = _generator(resolver=lambda profession, lang: calls.append((profession, lang)))
    generator._generate_profile_rule_based = lambda **kwargs: {"profession": "", "mbti": "ISTJ"}
    entity = EntityNode("entity-1", "Samira", ["Expert"], "", {})
    profile = generator.generate_profile_from_entity(entity, user_id=4, use_llm=False)
    assert calls == []
    assert "<expertise_metier>" not in profile.system_prompt


def test_persona_context_skips_redundant_hybrid_graph_search_by_default():
    class _Storage:
        def search(self, **_kwargs):
            raise AssertionError("hybrid graph search must not run during persona preparation")

    class _WebEnricher:
        def enrich_if_needed(self, **_kwargs):
            return ""

    generator = object.__new__(WonderwallProfileGenerator)
    generator.storage = _Storage()
    generator.graph_id = "graph-1"
    generator.use_hybrid_graph_context = False
    generator.web_enricher = _WebEnricher()
    generator.simulation_requirement = "Test scenario"
    entity = EntityNode(
        "entity-1", "Google", ["TechGiant"], "", {},
        related_edges=[{"fact": "Google négocie avec le régulateur."}],
        related_nodes=[],
    )

    context = generator._build_entity_context(entity)

    assert "Google négocie avec le régulateur." in context
