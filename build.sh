#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Color definitions for clean logging
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

VENV_PYTHON="./venv/bin/python3"
VENV_TWINE="./venv/bin/twine"

echo -e "${YELLOW}=== Step 1: Cleaning old build artifacts and caches ===${NC}"
rm -rf dist/ build/ src/*.egg-info
echo -e "${GREEN}Clean complete.${NC}\n"

echo -e "${YELLOW}=== Step 2: Ensuring build tools are up to date ===${NC}"
if [ -f "$VENV_PYTHON" ]; then
    $VENV_PYTHON -m pip install --upgrade pip build twine setuptools wheel
else
    echo -e "${RED}Error: Virtual environment not found at ./venv/${NC}"
    exit 1
fi
echo -e "${GREEN}Build dependencies updated.${NC}\n"

echo -e "${YELLOW}=== Step 3: Packaging distribution (Wheel & Tarball) ===${NC}"
$VENV_PYTHON -m build
echo -e "${GREEN}Package built successfully.${NC}\n"

echo -e "${YELLOW}=== Step 4: Validating package metadata ===${NC}"
$VENV_TWINE check dist/*
echo -e "${GREEN}Metadata validation passed.${NC}\n"

# --- Target Selection Logic ---
echo -e "${YELLOW}=== Step 5: Select Upload Target ===${NC}"
echo "1) Private PyPI (local PyPICloud via Tailscale)"
echo "2) Production PyPI (real public repository)"
echo "3) Build only (Do not upload)"
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo -e "\n${YELLOW}Uploading to PRIVATE Forgejo repository...${NC}"
        # Updated target alias from 'private' to 'local-pypi' to sync with your ~/.pypirc profile config
        $VENV_TWINE upload -r local-pypi dist/*
        echo -e "${GREEN}Successfully published to local Forgejo! README will now render on your dashboard.${NC}"
        ;;
    2)
        echo -e "\n${RED}WARNING: You are about to publish to the REAL public PyPI!${NC}"
        read -p "Are you absolutely sure? (y/N): " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            $VENV_TWINE upload dist/*
            echo -e "${GREEN}Successfully published to live PyPI!${NC}"
        else
            echo -e "${YELLOW}Upload aborted.${NC}"
        fi
        ;;
    3)
        echo -e "\n${GREEN}Build artifacts kept in dist/. Exiting cleanly.${NC}"
        ;;
    *)
        echo -e "\n${RED}Invalid choice. Exiting without uploading.${NC}"
        exit 1
        ;;
esac
