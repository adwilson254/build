"""TDD coverage for the non-Rivian cleaner (scripts/rivian_cleaner.py).

Runs against a throwaway fake tree so the real opendbc checkout is untouched.
"""
import importlib.util
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_cleaner():
    path = os.path.join(REPO_ROOT, "scripts", "rivian_cleaner.py")
    spec = importlib.util.spec_from_file_location("rivian_cleaner", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cleaner = _load_cleaner()


def _make_car_tree(base):
    car = base / "opendbc_repo" / "opendbc" / "car"
    for brand in ("honda", "toyota", "hyundai", "rivian", "mock", "body", "common", "tests"):
        (car / brand).mkdir(parents=True)
        (car / brand / "__init__.py").write_text("")
    return car


def test_rename_disables_non_rivian_brands(tmp_path):
    car = _make_car_tree(tmp_path)
    cleaner.rename_disabled_directories(str(tmp_path))

    # non-allowed brands disabled
    assert (car / "honda_disabled").is_dir()
    assert (car / "toyota_disabled").is_dir()
    assert not (car / "honda").exists()
    # allowed brands + infra preserved
    for keep in ("rivian", "mock", "body", "common", "tests"):
        assert (car / keep).is_dir()
        assert not (car / f"{keep}_disabled").exists()


def test_rename_is_idempotent(tmp_path):
    _make_car_tree(tmp_path)
    cleaner.rename_disabled_directories(str(tmp_path))
    # second run must not error and must not create honda_disabled_disabled
    cleaner.rename_disabled_directories(str(tmp_path))
    car = tmp_path / "opendbc_repo" / "opendbc" / "car"
    assert (car / "honda_disabled").is_dir()
    assert not (car / "honda_disabled_disabled").exists()


def test_clean_file_regex_strips_non_allowed_brand_imports(tmp_path):
    values = tmp_path / "values.py"
    values.write_text(
        "from opendbc.car.honda.values import HONDA_CARS\n"
        "from opendbc.car.rivian.values import RIVIAN_CARS\n"
        "PLATFORM_HONDA = CAR.HONDA\n"
        "PLATFORM_RIVIAN = CAR.RIVIAN\n"
    )
    cleaner.clean_file_regex(str(values), cleaner.ALLOWED_CARS)
    out = values.read_text()
    assert "rivian" in out
    assert "RIVIAN" in out
    assert "honda" not in out
    assert "CAR.HONDA" not in out


def test_patch_sconscripts_injects_once_and_is_idempotent(tmp_path):
    sc = tmp_path / "system" / "loggerd" / "SConscript"
    sc.parent.mkdir(parents=True)
    sc.write_text("env = Environment()\nlibs += ['yuv']\nenv.Program(libs)\n")

    cleaner.patch_sconscripts(str(tmp_path))
    once = sc.read_text()
    # the va/drm guard is injected exactly once, right after the yuv line
    assert once.count("libs += ['va', 'va-drm', 'drm']") == 1
    assert 'if arch != "Darwin":' in once

    # running again must not double-inject (regression: the old code added the
    # drm libs twice in a single pass and re-added on re-runs)
    cleaner.patch_sconscripts(str(tmp_path))
    twice = sc.read_text()
    assert twice == once
    assert twice.count("libs += ['va', 'va-drm', 'drm']") == 1
