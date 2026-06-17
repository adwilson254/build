#!/usr/bin/env python3
"""Shared helpers for the Rivian feature injectors.

Keeps param-key registration consistent across inject_api / inject_mqtt /
inject_scores so each feature fully owns the params it uses, and main stays
pure upstream (params are added only into the generated `ap` build).
"""
import os

PARAMS_ANCHOR = "keys = {\n"


def add_param_keys(base_dir, entries):
    """Idempotently add ParamKey entries to common/params_keys.h.

    entries: list of (key_name, cpp_map_line) where cpp_map_line is the full C++
    map entry without indentation/newline, e.g.
        ('MqttEnabled', '{"MqttEnabled", {PERSISTENT | BACKUP, BOOL, "0"}},')

    Returns the list of keys actually added.
    """
    path = os.path.join(base_dir, 'common', 'params_keys.h')
    if not os.path.exists(path):
        print(f"Warning: {path} not found; cannot register param keys.")
        return []

    with open(path) as f:
        content = f.read()

    if PARAMS_ANCHOR not in content:
        print("Warning: could not find params_keys anchor; skipping param registration.")
        return []

    added = []
    block = ""
    for key, line in entries:
        if f'"{key}"' in content or f'"{key}"' in block:
            continue
        block += "    " + line + "\n"
        added.append(key)

    if block:
        content = content.replace(PARAMS_ANCHOR, PARAMS_ANCHOR + block, 1)
        with open(path, 'w') as f:
            f.write(content)
        print(f"Registered param keys: {', '.join(added)}")
    return added
