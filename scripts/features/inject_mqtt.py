#!/usr/bin/env python3
import os
import shutil
import re

def inject_mqtt():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src_dir = os.path.join(base_dir, 'scripts', 'features', 'src', 'rivian')
    dest_dir = os.path.join(base_dir, 'selfdrive', 'rivian')

    # Ensure selfdrive/rivian exists
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        with open(os.path.join(dest_dir, '__init__.py'), 'w') as f:
            f.write("")
        print(f"Created {dest_dir}")

    # Copy mqttd.py
    src_file = os.path.join(src_dir, 'mqttd.py')
    dest_file = os.path.join(dest_dir, 'mqttd.py')
    if os.path.exists(src_file):
        shutil.copy2(src_file, dest_file)
        print(f"Injected {dest_file}")
    else:
        print(f"Error: {src_file} not found. Cannot inject MQTT daemon.")
        return

    # Patch system/manager/process_config.py
    process_config_path = os.path.join(base_dir, 'system', 'manager', 'process_config.py')
    with open(process_config_path, 'r') as f:
        content = f.read()

    # Inject mqtt_enabled helper if not present
    if "def mqtt_enabled(" not in content:
        helper_code = "\n\ndef mqtt_enabled(started: bool, params: Params, CP: car.CarParams) -> bool:\n  return params.get_bool(\"MqttEnabled\")\n"
        # Find procs = [ and inject right before it
        content = content.replace("procs = [", helper_code + "\nprocs = [", 1)
        print("Injected mqtt_enabled helper into process_config.py")

    # Inject mqttd process if not present
    if '"mqttd"' not in content:
        proc_code = '  PythonProcess("mqttd", "selfdrive.rivian.mqttd", mqtt_enabled),'
        # find the end of the procs array (before # debug procs) or just append it to the procs array
        if "# debug procs" in content:
            content = content.replace("# debug procs", proc_code + "\n\n  # debug procs", 1)
        else:
            print("Warning: Could not find anchor for mqttd process injection.")
        print("Injected mqttd process into process_config.py")

    with open(process_config_path, 'w') as f:
        f.write(content)

    # Patch pyproject.toml
    pyproject_path = os.path.join(base_dir, 'pyproject.toml')
    with open(pyproject_path, 'r') as f:
        pyproject = f.read()
    
    if '"paho-mqtt"' not in pyproject and "'paho-mqtt'" not in pyproject:
        # Find dependencies = [ and inject it
        pyproject = re.sub(r'(dependencies\s*=\s*\[)', r'\1\n  "paho-mqtt",', pyproject)
        with open(pyproject_path, 'w') as f:
            f.write(pyproject)
        print("Injected paho-mqtt into pyproject.toml")
    else:
        print("paho-mqtt already exists in pyproject.toml")

    print("MQTT injection complete.")

if __name__ == '__main__':
    inject_mqtt()
