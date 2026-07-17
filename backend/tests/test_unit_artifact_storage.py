"""Tests unitaires US-221 — artifact_storage (persistance durable, ADR-005).

Vérifie :
  - sync_directory_to_storage : upload + indexation, résilience Supabase absent,
    résilience à l'échec d'un fichier individuel
  - is_durably_persisted : reflète la présence d'artefacts indexés
  - ensure_simulation_dir_hydrated : no-op si contenu local présent, résilience
    Supabase absent/injoignable, rematérialisation réelle depuis Storage
  - round-trip complet (AC2) : sync -> suppression du dossier local -> hydrate
    reconstruit exactement le même contenu, sans Supabase réel (fake client
    in-memory partagé entre les deux appels)
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.auth.supabase_client import SupabaseConfigError
from app.services import artifact_storage


class _FakeBucket:
    """Bucket Storage factice : stocke le contenu uploadé en mémoire."""

    def __init__(self, blobs: dict):
        self._blobs = blobs
        self.upload_calls = []
        self.download_calls = []

    def upload(self, storage_path, fh, file_options=None):
        self.upload_calls.append(storage_path)
        self._blobs[storage_path] = fh.read()

    def download(self, storage_path):
        self.download_calls.append(storage_path)
        return self._blobs[storage_path]


class _FakeSupabaseClient:
    """Client Supabase factice : bucket in-memory + table simulation_artifacts in-memory."""

    def __init__(self):
        self._blobs: dict = {}
        self._rows: dict = {}  # (simulation_id, relative_path) -> row dict
        self.storage = SimpleNamespace(from_=lambda bucket_id: _FakeBucket(self._blobs))

    def table(self, name):
        assert name == "simulation_artifacts"
        return _FakeTable(self)


class _FakeTable:
    def __init__(self, client: _FakeSupabaseClient):
        self._client = client
        self._filter_simulation_id = None

    def upsert(self, row, on_conflict=None):
        key = (row["simulation_id"], row["relative_path"])
        self._client._rows[key] = row
        return self

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        assert field == "simulation_id"
        self._filter_simulation_id = value
        return self

    def execute(self):
        rows = [
            row for (sim_id, _rel), row in self._client._rows.items()
            if sim_id == self._filter_simulation_id
        ]
        return SimpleNamespace(data=rows)


def _write_files(directory: str, files: dict) -> None:
    for relative_path, content in files.items():
        full_path = os.path.join(directory, *relative_path.split("/"))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as fh:
            fh.write(content)


class TestSyncDirectoryToStorage:
    def test_missing_local_dir_returns_zero_and_never_calls_supabase(self, tmp_path):
        client = MagicMock()
        result = artifact_storage.sync_directory_to_storage(
            "sim_absent", str(tmp_path / "does-not-exist"), client=client,
        )
        assert result == 0
        client.storage.from_.assert_not_called()

    def test_supabase_not_configured_returns_zero(self, tmp_path, monkeypatch):
        _write_files(str(tmp_path), {"state.json": b"{}"})

        def _raise_config_error():
            raise SupabaseConfigError("no config in tests")

        monkeypatch.setattr(artifact_storage, "get_supabase_admin", _raise_config_error)
        result = artifact_storage.sync_directory_to_storage("sim_1", str(tmp_path))
        assert result == 0

    def test_uploads_each_file_and_indexes_metadata(self, tmp_path):
        _write_files(str(tmp_path), {
            "state.json": b'{"status": "ready"}',
            "twitter/actions.jsonl": b'{"a": 1}\n',
        })
        client = _FakeSupabaseClient()

        synced = artifact_storage.sync_directory_to_storage("sim_2", str(tmp_path), client=client)

        assert synced == 2
        indexed_paths = {row["relative_path"] for row in client._rows.values()}
        assert indexed_paths == {"state.json", "twitter/actions.jsonl"}
        for row in client._rows.values():
            assert row["storage_path"] == f"simulations/sim_2/{row['relative_path']}"
            assert row["size_bytes"] > 0

    def test_one_file_failure_does_not_block_the_others(self, tmp_path):
        _write_files(str(tmp_path), {"good.json": b"{}", "bad.json": b"{}"})
        client = _FakeSupabaseClient()

        real_upload = client.storage.from_("simulation-artifacts").upload

        def _flaky_upload(storage_path, fh, file_options=None):
            if storage_path.endswith("bad.json"):
                raise RuntimeError("simulated network blip")
            return real_upload(storage_path, fh, file_options=file_options)

        bucket = SimpleNamespace(upload=_flaky_upload, download=lambda p: client._blobs[p])
        client.storage = SimpleNamespace(from_=lambda bucket_id: bucket)

        synced = artifact_storage.sync_directory_to_storage("sim_3", str(tmp_path), client=client)

        assert synced == 1
        assert {row["relative_path"] for row in client._rows.values()} == {"good.json"}


class TestIsDurablyPersisted:
    def test_true_when_artifacts_indexed(self):
        client = _FakeSupabaseClient()
        client._rows[("sim_4", "state.json")] = {
            "simulation_id": "sim_4", "relative_path": "state.json",
            "storage_path": "simulations/sim_4/state.json",
        }
        assert artifact_storage.is_durably_persisted("sim_4", client=client) is True

    def test_false_when_no_artifacts_indexed(self):
        client = _FakeSupabaseClient()
        assert artifact_storage.is_durably_persisted("sim_5", client=client) is False

    def test_false_on_supabase_config_error(self, monkeypatch):
        def _raise_config_error():
            raise SupabaseConfigError("no config in tests")

        monkeypatch.setattr(artifact_storage, "get_supabase_admin", _raise_config_error)
        assert artifact_storage.is_durably_persisted("sim_6") is False


class TestEnsureSimulationDirHydrated:
    def test_noop_when_local_dir_already_has_content(self, tmp_path):
        _write_files(str(tmp_path), {"state.json": b"{}"})
        client = MagicMock()
        result = artifact_storage.ensure_simulation_dir_hydrated(
            "sim_7", str(tmp_path), client=client,
        )
        assert result is True
        client.table.assert_not_called()

    def test_returns_false_when_dir_absent_and_supabase_not_configured(self, tmp_path, monkeypatch):
        def _raise_config_error():
            raise SupabaseConfigError("no config in tests")

        monkeypatch.setattr(artifact_storage, "get_supabase_admin", _raise_config_error)
        result = artifact_storage.ensure_simulation_dir_hydrated(
            "sim_8", str(tmp_path / "absent"),
        )
        assert result is False

    def test_returns_false_when_no_artifacts_indexed(self, tmp_path):
        client = _FakeSupabaseClient()
        result = artifact_storage.ensure_simulation_dir_hydrated(
            "sim_9", str(tmp_path / "absent"), client=client,
        )
        assert result is False

    def test_rematerializes_files_from_storage(self, tmp_path):
        client = _FakeSupabaseClient()
        client._blobs["simulations/sim_10/state.json"] = b'{"status": "ready"}'
        client._rows[("sim_10", "state.json")] = {
            "simulation_id": "sim_10", "relative_path": "state.json",
            "storage_path": "simulations/sim_10/state.json",
        }

        local_dir = str(tmp_path / "sim_10")
        result = artifact_storage.ensure_simulation_dir_hydrated("sim_10", local_dir, client=client)

        assert result is True
        with open(os.path.join(local_dir, "state.json"), "rb") as fh:
            assert fh.read() == b'{"status": "ready"}'


class TestRoundTripSurvivesLocalDeletion:
    """AC2 — après suppression simulée du dossier local, l'hydratation reconstruit le contenu."""

    def test_sync_then_delete_then_hydrate_reconstructs_directory(self, tmp_path):
        local_dir = str(tmp_path / "sim_11")
        _write_files(local_dir, {
            "state.json": b'{"status": "completed"}',
            "twitter/actions.jsonl": b'{"round": 1}\n{"round": 2}\n',
        })
        client = _FakeSupabaseClient()

        synced = artifact_storage.sync_directory_to_storage("sim_11", local_dir, client=client)
        assert synced == 2

        # Simule le volume Coolify éphémère vidé au redeploy.
        import shutil
        shutil.rmtree(local_dir)
        assert not os.path.isdir(local_dir)

        assert artifact_storage.is_durably_persisted("sim_11", client=client) is True

        hydrated = artifact_storage.ensure_simulation_dir_hydrated("sim_11", local_dir, client=client)
        assert hydrated is True

        with open(os.path.join(local_dir, "state.json"), "rb") as fh:
            assert fh.read() == b'{"status": "completed"}'
        with open(os.path.join(local_dir, "twitter", "actions.jsonl"), "rb") as fh:
            assert fh.read() == b'{"round": 1}\n{"round": 2}\n'
