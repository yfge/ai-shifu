# GitHub Environment Setup Guide

## Overview

This guide explains how to set up GitHub Environments for the three-stage release workflow with required reviewers and approval gates.

## Environment Configuration

### 1. Create Release Environment

1. Go to your GitHub repository
2. Navigate to **Settings** → **Environments**
3. Click **New environment**
4. Name it: `release`

### 2. Configure Required Reviewers

In the `release` environment settings:

1. **Required reviewers**: Add team members who should approve releases
   - Recommended: At least 1-2 senior developers or maintainers
   - Example: `@username1, @username2`

2. **Prevent self-review**: ✅ Enable (prevents the person creating the release from approving it themselves)

3. **Required reviewers can review their own request**: ❌ Disable (for better security)

### 3. Additional Security Settings (Optional)

- **Deployment branches**: Restrict to `main` branch only
- **Environment secrets**: Add any release-specific secrets if needed

## Usage in Workflows

The environment is referenced in `publish-release.yml`:

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    environment: release  # This triggers the approval gate
```

## Approval Flow

1. **prepare-release.yml** runs without approval (creates draft)
2. **publish-release.yml** requires approval when it reaches the `environment: release` job
3. GitHub will:
   - Pause the workflow
   - Send notifications to required reviewers
   - Wait for approval before continuing
4. After approval, the workflow continues and publishes the release
5. **build-on-release.yml** automatically triggers after publishing

## Notification Settings

Reviewers will receive notifications via:
- GitHub notifications
- Email (if enabled in user settings)
- Slack/Teams (if integrations are configured)

## Testing

To test the approval flow:
1. Create a test release using prepare-release.yml
2. Run publish-release.yml
3. Verify that the workflow pauses at the environment step
4. Have a reviewer approve the deployment
5. Confirm the workflow continues and completes

## Best Practices

1. **Minimum 2 reviewers**: Ensures no single point of failure
2. **Different time zones**: Consider having reviewers in different regions for 24/7 coverage
3. **Emergency process**: Document how to handle urgent releases outside business hours
4. **Regular review**: Periodically update the reviewer list as team members change
