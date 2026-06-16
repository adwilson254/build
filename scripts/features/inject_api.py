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

if __name__ == '__main__':
    inject_api()
