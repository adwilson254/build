"""TDD coverage for the feature injection scripts.

The pipeline re-runs these injectors on every upstream sync, so they MUST be:
  * correct      - they apply the expected patches
  * idempotent   - re-running never duplicates or corrupts patches
  * import-safe  - the patched process_config.py has no NameError-prone
                   annotations (the bug this whole effort started with)

The injectors are exercised against a throwaway base_dir so the real working
tree is never touched.
"""
import ast
import importlib.util
import os
import shutil

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FEATURES = os.path.join(REPO_ROOT, "scripts", "features")

# reuse the static annotation-safety analysis from the sibling test
import test_process_config_safe as safe  # noqa: E402


def _load(modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(FEATURES, f"{modname}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


inject_api = _load("inject_api").inject_api
inject_mqtt = _load("inject_mqtt").inject_mqtt
inject_web_ui = _load("inject_web").inject_web_ui
inject_scores = _load("inject_scores").inject_scores


PROCESS_CONFIG_STUB = '''\
from cereal import car
from openpilot.common.params import Params
from openpilot.system.manager.process import PythonProcess, NativeProcess, DaemonProcess


def always_run(started: bool, params: Params, CP: car.CarParams) -> bool:
  return True


def only_onroad(started: bool, params: Params, CP: car.CarParams) -> bool:
  return started


procs = [
  PythonProcess("logmessaged", "system.logmessaged", always_run),

  # debug procs
]
'''

PARAMS_KEYS_STUB = '''\
#pragma once
inline static std::unordered_map<std::string, ParamKeyAttributes> keys = {
    {"AccessToken", {CLEAR_ON_MANAGER_START | DONT_LOG, STRING}},
    {"AdbEnabled", {PERSISTENT | BACKUP, BOOL}},
};
'''


DEVELOPER_STUB = '''\
class DeveloperLayout:
  def __init__(self):
    self._adb_toggle = BigCircleParamControl(gui_app.texture("x"), "AdbEnabled")
    self._scroller.add_widgets([
      self._adb_toggle,
    ])
    self._refresh_toggles = (
      ("AdbEnabled", self._adb_toggle),
    )

  def _on_joystick_debug_mode(self, state: bool):
    pass
'''

PYPROJECT_STUB = '''\
[project]
name = "openpilot"
dependencies = [
  "numpy",
]
'''


@pytest.fixture
def base(tmp_path):
    """A minimal fake repo tree with real injector source files + target stubs."""
    root = tmp_path / "repo"
    # real source files the injectors copy from
    src_rivian = root / "scripts" / "features" / "src" / "rivian"
    src_web = root / "scripts" / "features" / "src" / "web_ui"
    src_rivian.mkdir(parents=True)
    (src_web / "frontend" / "dist").mkdir(parents=True)

    real_src = os.path.join(FEATURES, "src", "rivian")
    for f in ("api.py", "mqttd.py", "ui_api_snippet.py", "scorerd.py"):
        shutil.copy2(os.path.join(real_src, f), src_rivian / f)
    shutil.copy2(os.path.join(FEATURES, "src", "web_ui", "webd.py"), src_web / "webd.py")
    (src_web / "frontend" / "dist" / "index.html").write_text("<html></html>")

    # common/params_keys.h target for param-key registration
    common = root / "common"
    common.mkdir(parents=True)
    (common / "params_keys.h").write_text(PARAMS_KEYS_STUB)

    # target files to be patched
    dev = root / "selfdrive" / "ui" / "mici" / "layouts" / "settings"
    dev.mkdir(parents=True)
    (dev / "developer.py").write_text(DEVELOPER_STUB)

    mgr = root / "system" / "manager"
    mgr.mkdir(parents=True)
    (mgr / "process_config.py").write_text(PROCESS_CONFIG_STUB)

    (root / "pyproject.toml").write_text(PYPROJECT_STUB)
    return root


def _read(path):
    return open(path).read()


def _process_config(base):
    return str(base / "system" / "manager" / "process_config.py")


def _developer(base):
    return str(base / "selfdrive" / "ui" / "mici" / "layouts" / "settings" / "developer.py")


def _params_keys(base):
    return str(base / "common" / "params_keys.h")


def _assert_valid_python(path):
    ast.parse(_read(path))


def test_inject_api_copies_module_and_patches_ui(base):
    inject_api(base_dir=str(base))
    assert os.path.exists(base / "selfdrive" / "rivian" / "api.py")
    dev = _read(_developer(base))
    assert "self._rivian_login_btn = BigButton" in dev
    assert "RivianApiEnabled" in dev
    assert dev.startswith("import threading")
    _assert_valid_python(_developer(base))
    # api owns its param keys
    pk = _read(_params_keys(base))
    assert '"RivianApiEnabled"' in pk
    assert '"RivianApiToken"' in pk
    assert '"RivianApiStatus"' in pk


def test_inject_mqtt_patches_process_config_and_pyproject(base):
    inject_mqtt(base_dir=str(base))
    assert os.path.exists(base / "selfdrive" / "rivian" / "mqttd.py")
    pc = _read(_process_config(base))
    assert "def mqtt_enabled(" in pc
    assert '"mqttd"' in pc
    _assert_valid_python(_process_config(base))
    assert "paho-mqtt" in _read(base / "pyproject.toml")
    assert '"MqttEnabled"' in _read(_params_keys(base))


def test_inject_web_patches_process_config(base):
    inject_web_ui(base_dir=str(base))
    assert os.path.exists(base / "selfdrive" / "web_ui" / "webd.py")
    assert os.path.exists(base / "selfdrive" / "web_ui" / "frontend" / "dist" / "index.html")
    pc = _read(_process_config(base))
    assert "def web_ui_enabled(" in pc
    assert '"webd"' in pc
    _assert_valid_python(_process_config(base))


def test_inject_scores_registers_daemon_and_params(base):
    inject_scores(base_dir=str(base))
    assert os.path.exists(base / "selfdrive" / "rivian" / "scorerd.py")
    pc = _read(_process_config(base))
    assert '"scorerd"' in pc
    assert '"selfdrive.rivian.scorerd"' in pc
    _assert_valid_python(_process_config(base))
    pk = _read(_params_keys(base))
    assert '"RivianSmoothnessScore"' in pk
    assert '"RivianPathAccuracyScore"' in pk


def test_all_injectors_are_idempotent(base):
    # run the full pipeline twice
    for _ in range(2):
        inject_api(base_dir=str(base))
        inject_mqtt(base_dir=str(base))
        inject_web_ui(base_dir=str(base))
        inject_scores(base_dir=str(base))

    pc = _read(_process_config(base))
    dev = _read(_developer(base))
    pk = _read(_params_keys(base))

    # each patch must appear exactly once despite two runs
    assert pc.count("def mqtt_enabled(") == 1
    assert pc.count("def web_ui_enabled(") == 1
    assert pc.count('"mqttd"') == 1
    assert pc.count('"webd"') == 1
    assert pc.count('"scorerd"') == 1
    assert dev.count("self._rivian_login_btn = BigButton") == 1
    assert dev.count("import threading") == 1
    assert _read(base / "pyproject.toml").count("paho-mqtt") == 1

    # param keys must not be registered twice
    for key in ("RivianApiEnabled", "MqttEnabled", "RivianSmoothnessScore", "RivianPathAccuracyScore"):
        assert pk.count(f'"{key}"') == 1, f"{key} registered more than once"

    # refresh-toggle tuple entries must not accumulate either
    assert dev.count('("RivianApiEnabled", self._rivian_toggle)') == 1
    assert dev.count('("MqttEnabled", self._mqtt_toggle)') == 1

    _assert_valid_python(_process_config(base))
    _assert_valid_python(_developer(base))


def test_injectors_reach_a_fixed_point(base):
    """One pass and two passes must produce byte-identical output. Without this,
    every upstream sync would emit spurious (or accumulating) diffs."""
    def run():
        inject_api(base_dir=str(base))
        inject_mqtt(base_dir=str(base))
        inject_web_ui(base_dir=str(base))
        inject_scores(base_dir=str(base))

    run()
    snap_once = (_read(_developer(base)), _read(_process_config(base)), _read(_params_keys(base)))
    run()
    snap_twice = (_read(_developer(base)), _read(_process_config(base)), _read(_params_keys(base)))

    assert snap_once[0] == snap_twice[0], "developer.py is not a fixed point under re-injection"
    assert snap_once[1] == snap_twice[1], "process_config.py is not a fixed point under re-injection"
    assert snap_once[2] == snap_twice[2], "params_keys.h is not a fixed point under re-injection"


def test_injected_process_config_is_import_safe(base):
    """The injected process_config.py must not reintroduce the NameError bug:
    every annotation must resolve to a module-level name."""
    inject_mqtt(base_dir=str(base))
    inject_web_ui(base_dir=str(base))
    inject_scores(base_dir=str(base))

    tree = ast.parse(_read(_process_config(base)))
    available = safe._module_level_names(tree) | safe._ALWAYS_AVAILABLE
    unresolved = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        anns = [a.annotation for a in node.args.args if a.annotation]
        if node.returns:
            anns.append(node.returns)
        for ann in anns:
            for root in safe._annotation_root_names(ann):
                if root not in available:
                    unresolved.append(f"{node.name}: {root}")
    assert not unresolved, f"injected annotations not import-safe: {unresolved}"


import re as _re

ASSETS_ROOT = os.path.join(REPO_ROOT, "selfdrive", "assets")
DEVELOPER_REAL = os.path.join(
    REPO_ROOT, "selfdrive", "ui", "mici", "layouts", "settings", "developer.py"
)


def _texture_refs(src):
    """All asset paths referenced via gui_app.texture("...") in source text."""
    return _re.findall(r'gui_app\.texture\(\s*"([^"]+)"', src)


@pytest.mark.skipif(not os.path.exists(DEVELOPER_REAL), reason="developer.py not present on this branch")
def test_developer_texture_assets_exist():
    """Every gui_app.texture("...") in the real developer.py must point at an
    asset that actually exists.

    This guards the bug class that took the device down: an injected toggle
    referenced icons_mici/api_short.png / mqtt_short.png which don't exist, so
    the missing texture had orig_width=0 -> ZeroDivisionError at boot. Static
    parsing and container builds never caught it because the asset is only
    resolved at UI render time on-device.
    """
    src = open(DEVELOPER_REAL).read()
    missing = [
        ref for ref in _texture_refs(src)
        if not os.path.exists(os.path.join(ASSETS_ROOT, ref))
    ]
    assert not missing, f"developer.py references missing texture assets: {missing}"
