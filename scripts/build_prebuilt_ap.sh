#!/bin/bash
# Prebuilt 'ap' Branch Compiler Script
# Run this inside your openpilot-dev Docker container!

set -e

echo "=========================================="
echo "🚀 Building OpenRivian Prebuilt 'ap' Branch"
echo "=========================================="

# 0. Set up isolated Linux virtual environment
# We do this so we don't accidentally execute or overwrite the Mac's .venv
export UV_PROJECT_ENVIRONMENT="/home/batman/venv"
export VIRTUAL_ENV=$UV_PROJECT_ENVIRONMENT
export PATH="$VIRTUAL_ENV/bin:$PATH"

echo "[0/4] Syncing Linux dependencies..."
uv sync

# 1. Compile the code using all available cores
echo "[1/4] Compiling OpenPilot services (this may take a few minutes)..."
scons -j$(nproc) --minimal

# 2. Prepare the clean output directory
OUTPUT_DIR="prebuilt_ap"
echo "[2/4] Cleaning previous builds..."
rm -rf $OUTPUT_DIR
mkdir -p $OUTPUT_DIR

# 2.5 Ensure rsync is installed (openpilot-dev docker container doesn't have it by default)
if ! command -v rsync &> /dev/null; then
    echo "rsync not found. Installing it now..."
    sudo apt-get update && sudo apt-get install -y rsync || (apt-get update && apt-get install -y rsync)
fi

# 3. Strip massive source files and x86 binaries
echo "[3/4] Stripping source files and packaging..."
rsync -am \
  --exclude='.sconsign.dblite' \
  --exclude='*.a' \
  --exclude='*.o' \
  --exclude='*.os' \
  --exclude='*.pyc' \
  --exclude='moc_*' \
  --exclude='__pycache__' \
  --exclude='Jenkinsfile' \
  --exclude='**/release/' \
  --exclude='**/.github/' \
  --exclude='**/selfdrive/ui/replay/' \
  --exclude='**/__pycache__/' \
  --exclude='.git/' \
  --exclude='**/SConstruct' \
  --exclude='**/SConscript' \
  --exclude='**/.venv/' \
  --exclude='selfdrive/modeld/models/driving_vision.onnx' \
  --exclude='selfdrive/modeld/models/driving_policy.onnx' \
  --exclude='third_party/*x86*' \
  --exclude='third_party/*Darwin*' \
  --exclude='prebuilt_ap/' \
  --exclude='* 2.*' \
  --exclude='* 3.*' \
  --delete-excluded \
  ./ $OUTPUT_DIR/ || true

# 4. Prepare Git Repository for Push
echo "[4/4] Preparing Git repository in $OUTPUT_DIR..."
cd $OUTPUT_DIR
git init
git checkout -b ap
git add .
git commit -m "Auto-compiled prebuilt ap branch"

echo "=========================================="
echo "✅ Compilation Complete!"
echo "=========================================="
echo "The prebuilt code is ready inside the 'prebuilt_ap' folder."
echo ""
echo "Because Docker doesn't have your GitHub credentials, open a NEW terminal window on your Mac (outside of Docker) and run:"
echo ""
echo "cd prebuilt_ap"
echo "git remote add origin https://github.com/adwilson254/openpilot.git"
echo "GIT_LFS_SKIP_PUSH=1 git push -f origin ap"
echo "=========================================="
