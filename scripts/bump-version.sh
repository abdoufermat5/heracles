#!/bin/bash
# ============================================================================
# Version Bump Script for Heracles
# ============================================================================
# Usage: ./scripts/bump-version.sh <component> <bump-type>
#   component: api | ui | core | plugins
#   bump-type: major | minor | patch
#
# Examples:
#   ./scripts/bump-version.sh api patch    # 0.8.0-beta -> 0.8.1-beta
#   ./scripts/bump-version.sh ui minor     # 0.8.0-beta -> 0.9.0-beta
#   ./scripts/bump-version.sh core major   # 0.1.0 -> 1.0.0
# ============================================================================

set -e

COMPONENT=$1
BUMP_TYPE=$2

# Validate arguments
if [[ -z "$COMPONENT" || -z "$BUMP_TYPE" ]]; then
    echo "Usage: $0 <component> <bump-type>"
    echo "  component: api | ui | core | plugins"
    echo "  bump-type: major | minor | patch"
    exit 1
fi

if [[ ! "$COMPONENT" =~ ^(api|ui|core|plugins)$ ]]; then
    echo "Error: Invalid component '$COMPONENT'"
    echo "Valid components: api, ui, core, plugins"
    exit 1
fi

if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Error: Invalid bump type '$BUMP_TYPE'"
    echo "Valid types: major, minor, patch"
    exit 1
fi

# Determine file path and extraction pattern
case $COMPONENT in
    api)
        FILE="heracles-api/heracles_api/__init__.py"
        PATTERN='__version__\s*=\s*"([^"]+)"'
        ;;
    ui)
        FILE="heracles-ui/package.json"
        PATTERN='"version":\s*"([^"]+)"'
        ;;
    core)
        FILE="heracles-core/Cargo.toml"
        PATTERN='^version\s*=\s*"([^"]+)"'
        ;;
    plugins)
        FILE="heracles_plugins/pyproject.toml"
        PATTERN='^version\s*=\s*"([^"]+)"'
        ;;
esac

# Check file exists
if [[ ! -f "$FILE" ]]; then
    echo "Error: File not found: $FILE"
    exit 1
fi

# Extract current version
CURRENT_VERSION=$(grep -oP "$PATTERN" "$FILE" | head -1 | grep -oP '[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?')

if [[ -z "$CURRENT_VERSION" ]]; then
    echo "Error: Could not extract version from $FILE"
    exit 1
fi

# Parse version components
# Handle pre-release suffix (e.g., 0.8.0-beta)
BASE_VERSION=$(echo "$CURRENT_VERSION" | grep -oP '^[0-9]+\.[0-9]+\.[0-9]+')
SUFFIX=$(echo "$CURRENT_VERSION" | grep -oP '(-[a-zA-Z0-9]+)?$')

IFS='.' read -r MAJOR MINOR PATCH <<< "$BASE_VERSION"

# Calculate new version
case $BUMP_TYPE in
    major)
        NEW_MAJOR=$((MAJOR + 1))
        NEW_VERSION="${NEW_MAJOR}.0.0"
        # Major version removes pre-release suffix
        ;;
    minor)
        NEW_MINOR=$((MINOR + 1))
        NEW_VERSION="${MAJOR}.${NEW_MINOR}.0${SUFFIX}"
        ;;
    patch)
        NEW_PATCH=$((PATCH + 1))
        NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}${SUFFIX}"
        ;;
esac

# Update file based on component type
case $COMPONENT in
    api)
        sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" "$FILE"
        ;;
    ui)
        sed -i "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" "$FILE"
        ;;
    core)
        sed -i "0,/^version = \"$CURRENT_VERSION\"/s//version = \"$NEW_VERSION\"/" "$FILE"
        ;;
    plugins)
        sed -i "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" "$FILE"
        ;;
esac

echo "✓ Bumped heracles-$COMPONENT: $CURRENT_VERSION -> $NEW_VERSION"
