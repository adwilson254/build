"""Import-safety regression guard for system/manager/process_config.py.

openpilot evaluates function annotations at *import* time (there is no
`from __future__ import annotations` in process_config.py). A previous version of
the injected `web_ui_enabled` referenced `messaging.SubMaster` without importing
`messaging`, which raised `NameError` on import. Because conftest.py imports the
manager (which imports process_config), that single bug broke booting the device
*and* collection of the entire pytest suite.

This test catches that whole class of bug statically, with no compiled
artifacts, so it runs in the fast gate.
"""
import ast
import builtins
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESS_CONFIG = os.path.join(REPO_ROOT, "system", "manager", "process_config.py")

# Names made available implicitly (builtins + special forms used in annotations).
_ALWAYS_AVAILABLE = set(dir(builtins)) | {"None", "True", "False"}


def _module_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.add(tgt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _annotation_root_names(annotation: ast.expr) -> set[str]:
    """Root identifiers an annotation depends on, e.g. messaging.SubMaster -> {messaging}."""
    roots: set[str] = set()
    for sub in ast.walk(annotation):
        if isinstance(sub, ast.Name):
            roots.add(sub.id)
    return roots


def test_process_config_exists():
    assert os.path.exists(PROCESS_CONFIG), f"missing {PROCESS_CONFIG}"


def test_all_annotations_resolve_at_import_time():
    src = open(PROCESS_CONFIG).read()
    tree = ast.parse(src)
    available = _module_level_names(tree) | _ALWAYS_AVAILABLE

    unresolved: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        annotations = [a.annotation for a in (
            node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        ) if a.annotation is not None]
        if node.returns is not None:
            annotations.append(node.returns)
        for ann in annotations:
            for root in _annotation_root_names(ann):
                if root not in available:
                    unresolved.append(f"{node.name}: '{root}' (in '{ast.unparse(ann)}')")

    assert not unresolved, (
        "process_config.py has annotations referencing names not imported at "
        "module scope; these raise NameError at import time:\n  "
        + "\n  ".join(unresolved)
    )


def test_should_run_callbacks_have_consistent_arity():
    """should_run callbacks are invoked as cb(started, params, CP). Any callback
    passed to a *Process(...) must take 3 positional args so it doesn't blow up
    at runtime."""
    src = open(PROCESS_CONFIG).read()
    tree = ast.parse(src)

    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    # Collect callback names referenced as the 3rd positional arg of *Process(...)
    process_ctors = {"PythonProcess", "NativeProcess", "DaemonProcess"}
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in process_ctors:
            # find a bare Name arg that matches a locally defined should_run func
            for arg in node.args:
                if isinstance(arg, ast.Name) and arg.id in funcs:
                    referenced.add(arg.id)

    bad = []
    for name in referenced:
        fn = funcs[name]
        n_pos = len(fn.args.posonlyargs) + len(fn.args.args)
        if n_pos != 3:
            bad.append(f"{name} takes {n_pos} positional args, expected 3 (started, params, CP)")
    assert not bad, "should_run callbacks with wrong arity:\n  " + "\n  ".join(bad)
