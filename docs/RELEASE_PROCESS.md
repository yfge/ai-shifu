# Three-Stage Release Process Guide

## Overview

AI-Shifu now uses a secure, three-stage release process that separates draft preparation, human approval, and automated deployment. This ensures better control, prevents accidental releases, and provides approval gates for production deployments.

## Workflow Architecture

```
prepare-release.yml → publish-release.yml → build-on-release.yml
     (Draft)            (Approval)           (Automated)
```

### Stage 1: Prepare Release Draft
**File**: `.github/workflows/prepare-release.yml`
**Trigger**: Manual (workflow_dispatch)
**Purpose**: Create a draft release without triggering builds

### Stage 2: Publish Release
**File**: `.github/workflows/publish-release.yml`
**Trigger**: Manual + Human Approval Required
**Purpose**: Publish the release after review and approval

### Stage 3: Build and Deploy
**File**: `.github/workflows/build-on-release.yml`
**Trigger**: Automatic (on release published)
**Purpose**: Build Docker images and deploy automatically

## Prerequisites

### 1. GitHub Environment Setup

First, configure the `release` environment with required reviewers:

1. Go to **Settings** → **Environments** → **New environment**
2. Name: `release`
3. Add **Required reviewers** (recommend 1-2 senior developers)
4. Enable **Prevent self-review**

See [Environment Setup Guide](./ENVIRONMENT_SETUP.md) for detailed instructions.

### 2. Required Secrets

Ensure these secrets are configured in repository settings:

- `PAT_TOKEN` (optional, falls back to `GITHUB_TOKEN`)
- `DOCKERHUB_USER` and `DOCKERHUB_TOKEN` (for Docker Hub)
- `ALIYUN_USER` and `ALIYUN_TOKEN` (for Aliyun registry)

## Step-by-Step Release Process

### Step 1: Prepare Release Draft

1. Go to **Actions** → **Prepare Release Draft**
2. Click **Run workflow**
3. Enter version (e.g., `v1.2.3`)
4. Click **Run workflow**

**What happens:**
- ✅ Validates version format and checks for duplicates
- ✅ Updates version files (`package.json`, `docker-compose.prod.yml`)
- ✅ Generates changelog from commits since last release
- ✅ Creates a **draft** GitHub release
- ✅ Commits version changes to the repository
- ❌ **Does NOT** create git tags or trigger builds

**Output**: A draft release ready for review

### Step 2: Review and Publish

1. **Review the draft release**:
   - Check the generated changelog
   - Verify version numbers are correct
   - Test if needed using the updated version files

2. **Publish the release**:
   - Go to **Actions** → **Publish Release**
   - Click **Run workflow**
   - Enter the same version tag (e.g., `v1.2.3`)
   - Click **Run workflow**

3. **Approval process**:
   - The workflow will pause at the approval gate
   - Configured reviewers receive notifications
   - At least one reviewer must approve before proceeding

**What happens after approval:**
- ✅ Creates and pushes git tag
- ✅ Publishes the GitHub release (removes draft status)
- ✅ Triggers the automated build process

### Step 3: Automated Build and Deploy

This happens automatically when Stage 2 completes:

**What happens:**
- ✅ Validates the published release (skips prereleases)
- ✅ Builds Docker images for all services (API, Web, Cook Web)
- ✅ Supports multi-platform builds (linux/amd64, linux/arm64)
- ✅ Pushes to Docker Hub and/or Aliyun registry
- ✅ Updates repository descriptions
- ✅ Provides deployment summary and quick-start commands

## Quick Reference Commands

### For Docker Deployment

After a release is published and built:

```bash
# Pull the latest release images
docker pull aishifu/ai-shifu-api:v1.2.3
docker pull aishifu/ai-shifu-web:v1.2.3
docker pull aishifu/ai-shifu-cook-web:v1.2.3

# Start with production configuration
cd docker
docker compose -f docker-compose.prod.yml up -d
```

### For Development

```bash
# The docker-compose.prod.yml file is automatically updated
# to reference the new version tags
git pull  # Get the updated version files
cd docker
docker compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

1. **"No release found for tag"**
   - Make sure you ran Stage 1 (Prepare Release Draft) first
   - Check that the tag name matches exactly

2. **"Release is not a draft"**
   - The release has already been published
   - You can't publish the same release twice

3. **Workflow stuck on approval**
   - Check that required reviewers are notified
   - Ensure reviewers have proper permissions
   - Verify environment configuration

4. **Build fails automatically**
   - Check Docker registry credentials
   - Verify Dockerfile paths and build contexts
   - Review build logs for specific errors

### Emergency Release Process

For urgent releases outside business hours:

1. **Temporarily bypass approval** (if needed):
   - Remove the `environment: release` line from `publish-release.yml`
   - Restore it after the emergency release

2. **Quick hotfix**:
   - Create hotfix branch from the release tag
   - Make minimal changes
   - Follow the normal three-stage process

## Migration from Legacy Process

### For Existing Projects

The old single-stage `release.yml` has been renamed to `release-legacy.yml` and marked as deprecated.

**To migrate:**

1. ✅ Set up the GitHub Environment (see prerequisites)
2. ✅ Use the new three-stage process for all future releases
3. ❌ Avoid using the legacy workflow

### Changelog Generation

The new process maintains the same changelog generation logic:
- Uses `commitizen` for conventional commit parsing
- Falls back to manual parsing if needed
- Supports initial releases with README.md content
- Generates incremental changelogs from the previous tag

## Best Practices

### Version Numbering

- Use semantic versioning: `v1.2.3`
- Always include the `v` prefix
- Consider using pre-release suffixes for testing: `v1.2.3-beta.1`

### Release Timing

- **Prepare drafts** can be done anytime during development
- **Publish releases** during business hours when reviewers are available
- **Builds happen automatically** - no timing concerns

### Review Process

- At least 2 reviewers for production releases
- Review the changelog and version changes carefully
- Test critical functionality before approval
- Document any known issues in the release notes

### Rollback Strategy

If issues are discovered after release:

1. **Immediate**: Revert to previous Docker image tags manually
2. **Proper fix**: Create a new hotfix release following the same process
3. **Communication**: Update release notes with any issues or workarounds

## Monitoring and Notifications

### GitHub Notifications

- Release reviewers receive notifications automatically
- Workflow status is visible in the Actions tab
- Release notes are published to the repository

### Integration Options

Consider integrating with:
- Slack/Teams for team notifications
- Email alerts for critical releases
- Deployment monitoring tools
- Issue tracking systems for release notes

---

## Summary

The three-stage process provides:
- ✅ **Safety**: Draft stage prevents accidental releases
- ✅ **Control**: Human approval required for production
- ✅ **Automation**: Builds happen automatically after approval
- ✅ **Auditability**: Clear trail of who approved what
- ✅ **Flexibility**: Each stage can be run independently

This replaces the previous single-stage workflow while maintaining all the same functionality with better security and control.
