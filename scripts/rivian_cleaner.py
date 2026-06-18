#!/usr/bin/env python3
import os
import re
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

def _import_brand(line):
    """Return the opendbc car brand a line imports from, else None.

    Handles `from opendbc.car.<brand>...`, `from opendbc.sunnypilot.car.<brand>...`
    and `import opendbc.car.<brand>...`. Non-brand submodules (interfaces, values,
    common, ...) are returned as-is and filtered by the disabled-brand check.
    """
    for marker, idx in (("from opendbc.car.", 2), ("from opendbc.sunnypilot.car.", 3)):
        if line.startswith(marker):
            parts = line.split(".")
            if len(parts) > idx:
                return parts[idx].split(" ")[0].strip()
    if "opendbc.car." in line and "import" in line:
        return line.split("opendbc.car.")[1].split(".")[0].split(" ")[0].strip()
    return None


def clean_file_regex(filepath, allowed_brands, disabled_brands):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}, not found.")
        return

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Pass 1: collect the aliases that disabled-brand imports introduce, e.g.
    #   from opendbc.car.honda.values import CAR as HONDA   -> alias "HONDA"
    # so we can also drop later references like `HONDA.ACURA_ILX` (e.g. in the
    # MIGRATION dict), which would otherwise NameError once the import is gone.
    removed_aliases = set()
    for line in lines:
        brand = _import_brand(line)
        if brand in disabled_brands and " as " in line:
            alias = line.split(" as ", 1)[1].strip().split()[0].rstrip(",")
            if alias:
                removed_aliases.add(alias)
    alias_res = [re.compile(r"\b" + re.escape(a) + r"\.") for a in removed_aliases]

    new_lines = []
    for line in lines:
        # Drop imports for actual disabled brands (never non-brand submodules).
        if _import_brand(line) in disabled_brands:
            continue
        # Drop any line referencing a removed brand alias (MIGRATION entries, etc.).
        if alias_res and any(r.search(line) for r in alias_res):
            continue
        # Drop dict entries referencing a disabled brand via CAR.<BRAND>.
        if "CAR." in line and any(b.upper() in line for b in disabled_brands):
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

def disabled_brands(base_dir=BASE_DIR):
    """Set of car brand names that have been disabled (renamed to *_disabled)."""
    brands = set()
    for car_dir in (os.path.join(base_dir, "opendbc_repo", "opendbc", "car"),
                    os.path.join(base_dir, "opendbc_repo", "opendbc", "sunnypilot", "car")):
        if not os.path.isdir(car_dir):
            continue
        for d in os.listdir(car_dir):
            if d.endswith("_disabled") and os.path.isdir(os.path.join(car_dir, d)):
                brands.add(d[:-len("_disabled")])
    return brands


def run_all(base_dir=BASE_DIR):
    rename_disabled_directories(base_dir)
    disabled = disabled_brands(base_dir)
    clean_file_regex(os.path.join(base_dir, "opendbc_repo", "opendbc", "car", "values.py"), ALLOWED_CARS, disabled)
    clean_file_regex(os.path.join(base_dir, "opendbc_repo", "opendbc", "car", "fingerprints.py"), ALLOWED_CARS, disabled)
    copy_templates(base_dir)
    patch_sconscripts(base_dir)


if __name__ == "__main__":
    print("Running Rivian Cleaner...")
    run_all()
    print("Done!")
