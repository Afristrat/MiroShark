"""Regression tests for fresh simulation-run cleanup."""

from app.services.simulation_runner import SimulationRunner


def test_cleanup_removes_each_platform_database_but_keeps_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path))
    sim_dir = tmp_path / "sim_cleanup"
    sim_dir.mkdir()
    for filename in (
        "twitter_simulation.db",
        "reddit_simulation.db",
        "polymarket_simulation.db",
    ):
        (sim_dir / filename).write_bytes(b"sqlite")
    config = sim_dir / "simulation_config.json"
    config.write_text("{}", encoding="utf-8")

    result = SimulationRunner.cleanup_simulation_logs("sim_cleanup")

    assert result["success"] is True
    assert config.exists()
    assert not any((sim_dir / f"{platform}_simulation.db").exists() for platform in ("twitter", "reddit", "polymarket"))
