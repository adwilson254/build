#!/usr/bin/env python3
import os
import shutil

def inject_api():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src_dir = os.path.join(base_dir, 'scripts', 'features', 'src', 'rivian')
    dest_dir = os.path.join(base_dir, 'selfdrive', 'rivian')

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        with open(os.path.join(dest_dir, '__init__.py'), 'w') as f:
            f.write("")
        print(f"Created {dest_dir}")

    src_file = os.path.join(src_dir, 'api.py')
    dest_file = os.path.join(dest_dir, 'api.py')
    
    if os.path.exists(src_file):
        shutil.copy2(src_file, dest_file)
        print(f"Injected {dest_file}")
    else:
        print(f"Error: {src_file} not found. Cannot inject API.")

    # Patch Developer UI for API features
    developer_ui_path = os.path.join(base_dir, 'selfdrive', 'ui', 'mici', 'layouts', 'settings', 'developer.py')
    if os.path.exists(developer_ui_path):
        with open(developer_ui_path, 'r') as f:
            content = f.read()
        
        dirty = False
        if "import threading" not in content:
            content = "import threading\n" + content
            dirty = True
            
        if "self._rivian_login_btn = BigButton" not in content:
            snippet_path = os.path.join(src_dir, 'ui_api_snippet.py')
            with open(snippet_path, 'r') as f:
                snippet = f.read()
            toggle_def = '    self._rivian_toggle = BigCircleParamControl(gui_app.texture("icons_mici/api_short.png", 82, 82), "RivianApiEnabled", icon_offset=(0, 12))\n'
            anchor1 = '    self._adb_toggle = BigCircleParamControl'
            if anchor1 in content:
                content = content.replace(anchor1, snippet + "\n" + toggle_def + anchor1)
                dirty = True

        try:
            widgets_block = content.split("self._scroller.add_widgets([")[1].split("]")[0]
            if "self._rivian_toggle" not in widgets_block:
                anchor2 = '      self._adb_toggle,'
                if anchor2 in content:
                    content = content.replace(anchor2, anchor2 + "\n      self._rivian_toggle,\n      self._rivian_login_btn,")
                    dirty = True
        except IndexError:
            pass

        try:
            toggles_block = content.split("self._refresh_toggles = (")[1].split(")")[0]
            if "RivianApiEnabled" not in toggles_block:
                anchor3 = '      ("AdbEnabled", self._adb_toggle),'
                if anchor3 in content:
                    content = content.replace(anchor3, anchor3 + '\n      ("RivianApiEnabled", self._rivian_toggle),')
                    dirty = True
        except IndexError:
            pass

        if "RivianApiStatus" not in content:
            refresh_code = """
    # Refresh Rivian status text
    rivian_status = None
    try:
      rivian_status = ui_state.params.get("RivianApiStatus")
    except BaseException:
      pass

    if rivian_status:
      status_str = rivian_status.decode('utf8') if hasattr(rivian_status, 'decode') else rivian_status
      if self._rivian_login_btn.value != status_str:
        self._rivian_login_btn.set_value(status_str)
"""
            anchor4 = "  def _on_joystick_debug_mode(self, state: bool):"
            if anchor4 in content:
                content = content.replace(anchor4, refresh_code + "\n" + anchor4)
                dirty = True
                
        if dirty:
            with open(developer_ui_path, 'w') as f:
                f.write(content)
            print("Injected UI API settings into developer.py")

if __name__ == '__main__':
    inject_api()
