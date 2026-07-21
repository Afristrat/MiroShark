from app.api.graph import _resolve_project_name


def test_explicit_project_name_has_priority():
    assert _resolve_project_name(
        "Acquisition audiovisuelle MENA",
        ["source.md"],
        [],
        "Une autre description",
    ) == "Acquisition audiovisuelle MENA"


def test_uploaded_filename_replaces_the_unnamed_project_fallback():
    assert _resolve_project_name(
        "Unnamed Project",
        ["Acquisition d'une startup AV IA en Europe et MENA.md"],
        [],
        "Simuler la réaction des parties prenantes.",
    ) == "Acquisition d'une startup AV IA en Europe et MENA"


def test_url_title_then_requirement_are_safe_fallbacks():
    assert _resolve_project_name(
        "",
        [],
        [{"title": "Analyse marché MENA"}],
        "Simuler la réaction des parties prenantes.",
    ) == "Analyse marché MENA"
    assert _resolve_project_name("", [], [], "  Simuler   une réponse   stratégique. ") == (
        "Simuler une réponse stratégique."
    )
