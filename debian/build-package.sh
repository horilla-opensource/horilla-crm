#!/bin/bash
# Build script for Horilla-CRM Debian package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building Horilla-CRM Debian package..."
echo "Project directory: $PROJECT_DIR"

cd "$PROJECT_DIR"

# Check if we have required build tools
if ! command -v dpkg-buildpackage &> /dev/null; then
    echo "Error: dpkg-buildpackage not found. Install with:"
    echo "  sudo apt-get install dpkg-dev debhelper"
    exit 1
fi

# Check if we have required dependencies
echo "Checking build dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

if ! python3 -c "import venv" &> /dev/null; then
    echo "Error: python3-venv not found. Install with:"
    echo "  sudo apt-get install python3-venv"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf debian/tmp*
rm -rf debian/horilla-crm*
rm -rf ../horilla-crm_*

# Build the package
echo "Building package..."
dpkg-buildpackage -us -uc -b

echo "Package build completed!"
echo "Generated files:"
ls -la ../horilla-crm_*

echo ""
echo "To install the package:"
echo "  sudo dpkg -i ../horilla-crm_*.deb"
echo "  sudo apt-get install -f  # If there are dependency issues"
echo ""
echo "To test the package:"
echo "  sudo systemctl start horilla-crm"
echo "  sudo systemctl status horilla-crm"
