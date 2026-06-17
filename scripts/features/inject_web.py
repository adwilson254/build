#!/usr/bin/env python3
import os
import re
import shutil


def validate_dist(dist_dir):
    """Ensure a built frontend bundle is self-consistent.

    Vite emits content-hashed asset filenames referenced from index.html. If the
    frontend wasn't (re)built, index.html points at assets that don't exist and
    the UI loads blank. We fail loudly here rather than ship a no-JS UI.

    Returns the list of referenced asset paths. Raises ValueError if broken.
    """
    index = os.path.join(dist_dir, 'index.html')
    if not os.path.exists(index):
        raise ValueError(f"dist missing index.html: {dist_dir}")
    html = open(index).read()
    refs = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html)
    missing = [r for r in refs if not os.path.exists(os.path.join(dist_dir, r.lstrip('/')))]
    if missing:
        raise ValueError(
            f"frontend dist at {dist_dir} references missing assets {missing}. "
            "Build the frontend first: (cd scripts/features/src/web_ui/frontend && npm ci && npm run build)"
        )
    return refs


def inject_web_ui(base_dir=None):
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src_dir = os.path.join(base_dir, 'scripts', 'features', 'src', 'web_ui')
    dest_dir = os.path.join(base_dir, 'selfdrive', 'web_ui')

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        with open(os.path.join(dest_dir, '__init__.py'), 'w') as f:
            f.write("")
        print(f"Created {dest_dir}")

    # Copy the daemon
    shutil.copy2(os.path.join(src_dir, 'webd.py'), os.path.join(dest_dir, 'webd.py'))
    
    # Copy the built frontend bundle
    src_frontend_dist = os.path.join(src_dir, 'frontend', 'dist')
    dest_frontend_dist = os.path.join(dest_dir, 'frontend', 'dist')
    
    if os.path.exists(src_frontend_dist):
        # Validate BEFORE destroying the destination so a broken source build
        # never clobbers a working one.
        validate_dist(src_frontend_dist)
        if os.path.exists(dest_frontend_dist):
            shutil.rmtree(dest_frontend_dist)
        shutil.copytree(src_frontend_dist, dest_frontend_dist)
        print("Copied compiled React frontend.")
    else:
        print("Warning: React frontend 'dist' directory not found. Please build it first.")

    # Patch process_config.py to add webd
    process_config_path = os.path.join(base_dir, 'system', 'manager', 'process_config.py')
    with open(process_config_path, 'r') as f:
        content = f.read()

    dirty = False
    
    # Add toggle helper
    if "def web_ui_enabled(" not in content:
        toggle_func = """
def web_ui_enabled(started: bool, params: Params, CP: car.CarParams) -> bool:
  # The Web UI runs constantly unless explicitly disabled
  return True
"""
        anchor = "procs = ["
        if anchor in content:
            content = content.replace(anchor, toggle_func + "\n" + anchor)
            dirty = True

    # Add PythonProcess to the list
    if '"webd"' not in content:
        # Find the end of the procs list or inject it at the top
        proc_entry = '  PythonProcess("webd", "selfdrive.web_ui.webd", web_ui_enabled),\n'
        anchor_proc = "procs = ["
        if anchor_proc in content:
            content = content.replace(anchor_proc, anchor_proc + "\n" + proc_entry)
            dirty = True

    if dirty:
        with open(process_config_path, 'w') as f:
            f.write(content)
        print("Injected webd into process_config.py")

    print("Web UI injection complete.")

if __name__ == '__main__':
    inject_web_ui()
