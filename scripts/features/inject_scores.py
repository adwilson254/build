#!/usr/bin/env python3
"""Inject the Rivian scoring daemon (scorerd).

Mirrors inject_api / inject_mqtt: copies the scorerd source into
selfdrive/rivian and registers it as a managed process. scorerd computes the
Smoothness / Path-Accuracy metrics consumed by mqttd and the Web UI.

Idempotent: re-running on an already-injected tree is a no-op.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inject_common import add_param_keys  # noqa: E402


def inject_scores(base_dir=None):
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src_dir = os.path.join(base_dir, 'scripts', 'features', 'src', 'rivian')
    dest_dir = os.path.join(base_dir, 'selfdrive', 'rivian')

    # Register the param keys this feature uses.
    add_param_keys(base_dir, [
        ("RivianSmoothnessScore", '{"RivianSmoothnessScore", {CLEAR_ON_MANAGER_START, FLOAT, "100.0"}},'),
        ("RivianPathAccuracyScore", '{"RivianPathAccuracyScore", {CLEAR_ON_MANAGER_START, FLOAT, "100.0"}},'),
    ])

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        with open(os.path.join(dest_dir, '__init__.py'), 'w') as f:
            f.write("")
        print(f"Created {dest_dir}")

    # Copy the scoring daemon
    src_file = os.path.join(src_dir, 'scorerd.py')
    dest_file = os.path.join(dest_dir, 'scorerd.py')
    if os.path.exists(src_file):
        shutil.copy2(src_file, dest_file)
        print(f"Injected {dest_file}")
    else:
        print(f"Error: {src_file} not found. Cannot inject scorerd.")
        return

    # Register scorerd as a managed process (runs onroad; uses carState/modelV2).
    process_config_path = os.path.join(base_dir, 'system', 'manager', 'process_config.py')
    with open(process_config_path, 'r') as f:
        content = f.read()

    if '"scorerd"' not in content:
        proc_entry = '  PythonProcess("scorerd", "selfdrive.rivian.scorerd", only_onroad),\n'
        anchor = "procs = ["
        if anchor in content:
            content = content.replace(anchor, anchor + "\n" + proc_entry, 1)
            with open(process_config_path, 'w') as f:
                f.write(content)
            print("Injected scorerd process into process_config.py")
        else:
            print("Warning: Could not find anchor 'procs = [' for scorerd injection.")
    else:
        print("scorerd already registered in process_config.py")


if __name__ == '__main__':
    inject_scores()
