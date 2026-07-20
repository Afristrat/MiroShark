from app.services.arena_routing import RoutingContext, parse_context, recommend


def test_private_diffusion_never_fakes_messaging_coverage():
    decision = recommend(RoutingContext("private_diffusion", ("family_networks",)))
    assert decision["recommended_arenas"] == ["twitter", "reddit"]
    assert {gap.get("arena") for gap in decision["coverage_gaps"]} == {"messaging_relay", None}
    assert decision["representativeness_status"] == "partial"


def test_measurable_market_outcome_adds_only_implemented_conviction_arena():
    decision = recommend(RoutingContext("market_outcome", outcome_measurable=True))
    assert decision["recommended_arenas"] == ["twitter", "reddit", "polymarket"]
    assert decision["coverage_gaps"] == []


def test_unmeasurable_market_outcome_does_not_add_conviction_arena():
    decision = recommend(RoutingContext("market_outcome", outcome_measurable=False))
    assert "polymarket" not in decision["recommended_arenas"]


def test_context_requires_known_type_and_typed_population_list():
    try:
        parse_context({"scenario_type": "unknown", "populations": []})
    except ValueError as exc:
        assert str(exc) == "unsupported scenario_type"
    else:
        raise AssertionError("expected ValueError")


def test_recommend_endpoint_matches_the_documented_contract():
    from app import create_app

    app = create_app()
    client = app.test_client()
    response = client.post(
        "/api/simulation/routing/recommend",
        json={
            "scenario_type": "private_diffusion",
            "populations": ["family_networks"],
            "outcome_measurable": False,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["recommended_arenas"] == ["twitter", "reddit"]
    assert payload["data"]["representativeness_status"] == "partial"


def test_recommend_endpoint_rejects_an_invalid_routing_context():
    from app import create_app

    app = create_app()
    response = app.test_client().post(
        "/api/simulation/routing/recommend",
        json={"scenario_type": "unknown", "populations": []},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error_code": "INVALID_ROUTING_CONTEXT",
        "error": "unsupported scenario_type",
    }
