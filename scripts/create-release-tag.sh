#!/bin/bash

# Script to create release tags for AI-Shifu project
# Usage: ./scripts/create-release-tag.sh [patch|minor|major] [message]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "This script must be run from within a git repository"
    exit 1
fi

# Check if commitizen is available
if ! command -v cz &> /dev/null; then
    log_warning "Commitizen not found. Installing..."
    pip install commitizen
fi

# Get current version from latest tag
CURRENT_TAG=$(git tag -l --sort=-version:refname | grep -E "^v[0-9]+\.[0-9]+\.[0-9]+" | head -1 || echo "")

if [ -z "$CURRENT_TAG" ]; then
    CURRENT_VERSION="0.0.0"
    log_info "No previous semantic version tags found. Starting from $CURRENT_VERSION"
else
    CURRENT_VERSION=$(echo "$CURRENT_TAG" | sed 's/^v//')
    log_info "Current version: $CURRENT_VERSION"
fi

# Parse current version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Determine bump type
BUMP_TYPE=${1:-"auto"}
COMMIT_MESSAGE=${2:-""}

case "$BUMP_TYPE" in
    "major")
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    "minor")
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    "patch")
        PATCH=$((PATCH + 1))
        ;;
    "auto")
        log_info "Analyzing recent commits to determine bump type..."

        # Get commits since last tag
        if [ -n "$CURRENT_TAG" ]; then
            COMMITS_SINCE_TAG=$(git log "$CURRENT_TAG"..HEAD --oneline)
        else
            COMMITS_SINCE_TAG=$(git log --oneline)
        fi

        if echo "$COMMITS_SINCE_TAG" | grep -q "^[a-f0-9]* \(feat\|BREAKING CHANGE\)"; then
            if echo "$COMMITS_SINCE_TAG" | grep -q "BREAKING CHANGE"; then
                BUMP_TYPE="major"
                MAJOR=$((MAJOR + 1))
                MINOR=0
                PATCH=0
            else
                BUMP_TYPE="minor"
                MINOR=$((MINOR + 1))
                PATCH=0
            fi
        elif echo "$COMMITS_SINCE_TAG" | grep -q "^[a-f0-9]* fix"; then
            BUMP_TYPE="patch"
            PATCH=$((PATCH + 1))
        else
            log_warning "No conventional commits found since last tag"
            BUMP_TYPE="patch"
            PATCH=$((PATCH + 1))
        fi
        ;;
    *)
        log_error "Invalid bump type: $BUMP_TYPE. Use 'major', 'minor', 'patch', or 'auto'"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
NEW_TAG="v$NEW_VERSION"

log_info "Bump type: $BUMP_TYPE"
log_info "New version: $NEW_VERSION"

# Check if tag already exists
if git tag -l | grep -q "^$NEW_TAG$"; then
    log_error "Tag $NEW_TAG already exists"
    exit 1
fi

# Show recent commits
log_info "Recent commits that will be included in this release:"
if [ -n "$CURRENT_TAG" ]; then
    git log --oneline --decorate "$CURRENT_TAG"..HEAD | head -10
else
    git log --oneline --decorate | head -10
fi

# Confirm with user
echo
read -p "Create release tag $NEW_TAG? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Tag creation cancelled"
    exit 0
fi

# Generate commit message if not provided
if [ -z "$COMMIT_MESSAGE" ]; then
    COMMIT_MESSAGE="bump: version $CURRENT_VERSION → $NEW_VERSION"
fi

# Create and push tag
log_info "Creating tag $NEW_TAG..."
git tag "$NEW_TAG" -m "$COMMIT_MESSAGE"

log_success "Tag $NEW_TAG created successfully"

# Ask if user wants to push the tag
read -p "Push tag to origin? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Pushing tag to origin..."
    git push origin "$NEW_TAG"
    log_success "Tag $NEW_TAG pushed to origin"
    log_info "GitHub Actions will now trigger the release workflow"
    log_info "Monitor the progress at: https://github.com/ai-shifu/ai-shifu/actions"
else
    log_warning "Tag created locally but not pushed"
    log_info "To push later: git push origin $NEW_TAG"
fi

log_success "Release tag creation completed!"
