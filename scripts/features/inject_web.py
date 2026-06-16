#!/usr/bin/env python3
import os
import shutil

def inject_web_ui():
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
def web_ui_enabled(CP: car.CarParams, sm: messaging.SubMaster, pm: messaging.PubMaster) -> bool:
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

    # Add webd to system/manager/manager.py to ensure it is managed
    manager_path = os.path.join(base_dir, 'system', 'manager', 'manager.py')
    if os.path.exists(manager_path):
        with open(manager_path, 'r') as f:
            manager_content = f.read()
        
        # openpilot's manager automatically reads from process_config.py
        # However, we must ensure it's not excluded anywhere. 
        # Typically no modification needed here, but we check just in case.

    print("Web UI injection complete.")

if __name__ == '__main__':
    inject_web_ui()
