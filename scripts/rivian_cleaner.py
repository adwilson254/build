#!/usr/bin/env python3
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_CARS = {'rivian', 'mock', 'body'}
ALLOWED_DIRS = ALLOWED_CARS.union({'common', 'include', 'tests', 'torque_data', 'debug'})

def rename_disabled_directories(base_dir=BASE_DIR):
    car_dirs = [
        os.path.join(base_dir, "opendbc_repo", "opendbc", "car"),
        os.path.join(base_dir, "opendbc_repo", "opendbc", "sunnypilot", "car")
    ]
    for car_dir in car_dirs:
        if not os.path.exists(car_dir):
            continue
        for folder in os.listdir(car_dir):
            path = os.path.join(car_dir, folder)
            if not os.path.isdir(path) or folder == "__pycache__":
                continue
            if folder in ALLOWED_DIRS or folder.endswith('_disabled'):
                continue
            
            # Disable folder
            new_path = path + "_disabled"
            if os.path.exists(new_path):
                shutil.rmtree(new_path)
            os.rename(path, new_path)
            print(f"Disabled: {path} -> {new_path}")

def clean_file_regex(filepath, allowed_brands):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}, not found.")
        return

    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []

    for line in lines:
        # Check for imports
        if line.startswith("from opendbc.car."):
            brand = line.split(".")[2]
            if brand not in allowed_brands and not brand.endswith('_disabled'):
                continue
        if line.startswith("from opendbc.sunnypilot.car."):
            brand = line.split(".")[3]
            if brand not in allowed_brands and not brand.endswith('_disabled'):
                continue
        
        # We also need to strip specific legacy lines like from opendbc.car.xyz import ...
        if "opendbc.car." in line and "import" in line:
            parts = line.split("opendbc.car.")
            if len(parts) > 1:
                brand = parts[1].split(".")[0].split(" ")[0]
                if brand not in allowed_brands and not brand.endswith('_disabled'):
                    continue
        
        # Basic filtering for dictionaries
        if "CAR." in line and not any(allowed.upper() in line for allowed in allowed_brands):
            # This handles PLATFORMS = { CAR.HONDA: ... }
            continue

        if line.startswith("Platform ="):
            allowed_upper = [a.upper() for a in allowed_brands]
            line = "Platform = " + " | ".join(allowed_upper) + "\n"

        new_lines.append(line)

    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    print(f"Cleaned regex: {filepath}")

def copy_templates(base_dir=BASE_DIR):
    templates = {
        "scripts/templates/car_specific.py": "selfdrive/car/car_specific.py",
        "scripts/templates/radard.py": "selfdrive/controls/radard.py",
        "scripts/templates/sunnypilot_interfaces.py": "opendbc_repo/opendbc/sunnypilot/car/interfaces.py",
        "scripts/templates/dbc.py": "opendbc_repo/opendbc/can/dbc.py"
    }
    for src_rel, dest_rel in templates.items():
        src = os.path.join(base_dir, src_rel)
        dest = os.path.join(base_dir, dest_rel)
        if os.path.exists(src):
            shutil.copy2(src, dest)
            print(f"Restored template: {dest}")
        else:
            print(f"Template not found: {src}")

def patch_sconscripts(base_dir=BASE_DIR):
    sconscripts = [
        "system/loggerd/SConscript",
        "tools/replay/SConscript",
        "tools/cabana/SConscript"
    ]
    for script in sconscripts:
        path = os.path.join(base_dir, script)
        if not os.path.exists(path):
            continue
        with open(path, 'r') as f:
            content = f.read()

        # Idempotent: skip if the va/drm libs were already injected.
        if "'drm'" in content:
            continue

        new_lines = []
        for line in content.split('\n'):
            new_lines.append(line)
            if line.strip() == "libs += ['yuv']":
                new_lines.append('  if arch != "Darwin":')
                new_lines.append("    libs += ['va', 'va-drm', 'drm']")
            elif "replay_libs =" in line and "base_libs" in line:
                new_lines.append('if arch != "Darwin":')
                new_lines.append("  replay_libs += ['va', 'va-drm', 'drm']")
            elif "cabana_libs =" in line and "base_libs" in line:
                new_lines.append('if arch != "Darwin":')
                new_lines.append("  cabana_libs += ['va', 'va-drm', 'drm']")

        content = '\n'.join(new_lines)
        with open(path, 'w') as f:
            f.write(content)
        print(f"Patched SConscript: {path}")

def run_all(base_dir=BASE_DIR):
    rename_disabled_directories(base_dir)
    clean_file_regex(os.path.join(base_dir, "opendbc_repo", "opendbc", "car", "values.py"), ALLOWED_CARS)
    clean_file_regex(os.path.join(base_dir, "opendbc_repo", "opendbc", "car", "fingerprints.py"), ALLOWED_CARS)
    copy_templates(base_dir)
    patch_sconscripts(base_dir)


if __name__ == "__main__":
    print("Running Rivian Cleaner...")
    run_all()
    print("Done!")
