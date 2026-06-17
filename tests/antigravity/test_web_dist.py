"""Guards against shipping a broken (no-JS) Web UI bundle.

vite emits content-hashed asset names referenced by index.html. If the frontend
isn't rebuilt, index.html points at assets that don't exist and the UI loads
blank. `inject_web.validate_dist` catches that; these tests pin its behavior and
verify the real source bundle once it has been built.
"""
import importlib.util
import os

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIST = os.path.join(REPO_ROOT, "scripts", "features", "src", "web_ui", "frontend", "dist")


def _load_validate():
    path = os.path.join(REPO_ROOT, "scripts", "features", "inject_web.py")
    spec = importlib.util.spec_from_file_location("inject_web", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate_dist


validate_dist = _load_validate()


def test_valid_dist_passes(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.js").write_text("//js")
    (tmp_path / "assets" / "index-abc123.css").write_text("/*css*/")
    (tmp_path / "index.html").write_text(
        '<script type="module" src="/assets/index-abc123.js"></script>'
        '<link rel="stylesheet" href="/assets/index-abc123.css">'
    )
    refs = validate_dist(str(tmp_path))
    assert set(refs) == {"/assets/index-abc123.js", "/assets/index-abc123.css"}


def test_missing_assets_raises(tmp_path):
    (tmp_path / "index.html").write_text(
        '<script type="module" src="/assets/index-missing.js"></script>'
    )
    with pytest.raises(ValueError, match="missing assets"):
        validate_dist(str(tmp_path))


def test_missing_index_raises(tmp_path):
    with pytest.raises(ValueError, match="index.html"):
        validate_dist(str(tmp_path))


def test_dist_with_no_asset_refs_is_ok(tmp_path):
    # static-only bundle (e.g. placeholder) is valid
    (tmp_path / "index.html").write_text("<html><body>ok</body></html>")
    assert validate_dist(str(tmp_path)) == []


def test_real_source_bundle_is_consistent_when_built():
    """If the frontend has been built (assets present), the source dist that the
    pipeline injects must be self-consistent. Skips on a fresh checkout where the
    bundle hasn't been built yet (the pipeline builds it before injecting)."""
    if not os.path.isdir(os.path.join(SRC_DIST, "assets")):
        pytest.skip("frontend not built yet (no dist/assets); pipeline builds before injecting")
    validate_dist(SRC_DIST)
