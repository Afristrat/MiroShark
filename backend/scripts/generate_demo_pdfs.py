"""Generate the 15 demo PDF briefs (5 slugs × 3 langs) for upcoming RDV.

Outputs to backend/uploads/demo_pdfs/. Run from the backend root:
    uv run python scripts/generate_demo_pdfs.py

The PDFs are produced through the same Flask test client as in tests, so the
output is byte-identical to what the live endpoint /api/models/<slug>/pdf-brief
would return.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_backend_on_path() -> Path:
    here = Path(__file__).resolve().parent
    backend_root = here.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    return backend_root


def _build_test_app():
    """Recreate the Flask app with non-essential dependencies stubbed."""
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "test")
    os.environ.setdefault("OPENROUTER_API_KEY", "sk-test")

    import app.storage as storage_mod

    class _NullStorage:
        def __init__(self, *a, **kw):
            pass

    original = storage_mod.Neo4jStorage
    storage_mod.Neo4jStorage = _NullStorage

    from app.services import simulation_runner as runner_mod
    original_cleanup = runner_mod.SimulationRunner.register_cleanup
    runner_mod.SimulationRunner.register_cleanup = classmethod(lambda cls: None)

    from app import create_app
    flask_app = create_app()

    storage_mod.Neo4jStorage = original
    runner_mod.SimulationRunner.register_cleanup = original_cleanup
    return flask_app


SLUGS = (
    "fusion-bancaire-mena",
    "crisis-drill-24h",
    "allocation-fonds-strategique",
    "stress-test-politique",
    "lancement-diaspora-eu",
)
LANGS = ("fr", "en", "ar")


def main() -> int:
    backend_root = _ensure_backend_on_path()
    out_dir = backend_root / "uploads" / "demo_pdfs"
    out_dir.mkdir(parents=True, exist_ok=True)

    app = _build_test_app()
    client = app.test_client()

    print(f"Output directory: {out_dir}")
    print(f"Generating {len(SLUGS) * len(LANGS)} PDFs ({len(SLUGS)} models × {len(LANGS)} languages)…")
    print()

    failures = []
    written = []
    for slug in SLUGS:
        for lang in LANGS:
            url = f"/api/models/{slug}/pdf-brief?lang={lang}"
            resp = client.get(url)
            if resp.status_code != 200:
                failures.append((slug, lang, resp.status_code, resp.data[:200]))
                print(f"  FAIL  {slug:32}  [{lang}]  HTTP {resp.status_code}")
                continue
            if resp.data[:5] != b"%PDF-":
                failures.append((slug, lang, "no-magic-bytes", resp.data[:20]))
                print(f"  FAIL  {slug:32}  [{lang}]  not a PDF stream")
                continue

            filename = f"bassira-modele-{slug}-{lang}.pdf"
            target = out_dir / filename
            target.write_bytes(resp.data)
            size_kb = len(resp.data) / 1024
            written.append(target)
            print(f"  OK    {slug:32}  [{lang}]  {size_kb:6.1f} kB  → {filename}")

    print()
    print(f"Wrote {len(written)} files to {out_dir}")
    if failures:
        print(f"FAILURES: {len(failures)}")
        for f in failures:
            print(f"  {f}")
        return 1
    print("All 15 PDFs generated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
