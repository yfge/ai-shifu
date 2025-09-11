# Testing Three-Stage Release Workflows

## Test Plan Overview

This document provides a comprehensive test plan for validating the new three-stage release process.

## Prerequisites for Testing

### 1. Environment Setup
- [ ] GitHub `release` environment created
- [ ] Required reviewers configured (at least one other team member)
- [ ] Repository secrets configured (PAT_TOKEN, Docker registry credentials)

### 2. Test Version Selection
Use a test version that doesn't conflict with existing releases:
- Suggested format: `v0.0.1-test`, `v0.0.2-test`, etc.
- Or use the next logical version number for your project

## Test Scenarios

### Test Case 1: Happy Path - Complete Release Process

**Objective**: Test the full three-stage release process from draft to deployment

**Steps**:

1. **Stage 1: Prepare Release Draft**
   ```
   Actions → Prepare Release Draft → Run workflow
   Version: v0.0.1-test
   ```

   **Expected Results**:
   - [ ] Workflow completes successfully
   - [ ] Draft release created in GitHub
   - [ ] Version files updated (package.json, docker-compose.prod.yml)
   - [ ] Changelog generated with proper content
   - [ ] Commit pushed with version changes
   - [ ] No git tag created yet
   - [ ] No Docker builds triggered

2. **Stage 2: Publish Release (with Approval)**
   ```
   Actions → Publish Release → Run workflow
   Tag: v0.0.1-test
   ```

   **Expected Results**:
   - [ ] Workflow starts and validates the draft release
   - [ ] Workflow pauses at approval gate
   - [ ] Reviewer receives notification
   - [ ] After approval, workflow continues
   - [ ] Git tag created and pushed
   - [ ] GitHub release published (no longer draft)
   - [ ] Release body cleaned (draft warning removed)

3. **Stage 3: Automatic Build and Deploy**

   **Expected Results** (automatic after Stage 2):
   - [ ] Build workflow triggers automatically
   - [ ] All three Docker images build successfully
   - [ ] Images pushed to configured registries
   - [ ] Build summary generated
   - [ ] Multi-platform support working (amd64, arm64)

### Test Case 2: Validation and Error Handling

**Objective**: Test input validation and error scenarios

**Sub-tests**:

1. **Invalid Version Format**
   - Try version without 'v' prefix: `1.0.0`
   - Try invalid format: `version-1`
   - Expected: Workflow fails with clear error message

2. **Duplicate Version**
   - Try to create draft for existing version
   - Expected: Workflow fails with "tag already exists" error

3. **Missing Draft Release**
   - Try to publish a tag that has no draft release
   - Expected: Publish workflow fails with "no release found" error

4. **Already Published Release**
   - Try to publish the same release twice
   - Expected: Publish workflow fails with "not a draft" error

### Test Case 3: Approval Process Testing

**Objective**: Test the human approval gate functionality

**Steps**:

1. **Self-Review Prevention**
   - Creator of release tries to approve their own release
   - Expected: GitHub prevents self-approval (if configured correctly)

2. **Multiple Reviewers**
   - Test with multiple required reviewers
   - Verify all required approvals are received

3. **Approval Notifications**
   - Verify reviewers receive GitHub notifications
   - Test email notifications (if configured)

### Test Case 4: Prerelease Handling

**Objective**: Test that prereleases are handled correctly

**Steps**:

1. Create a prerelease using GitHub UI or API
2. Verify that build workflow skips prerelease builds
3. Expected: Build workflow detects prerelease and skips building

### Test Case 5: First Release (No Previous Tags)

**Objective**: Test initial release when no previous tags exist

**Setup**: Use a clean repository or test repository with no existing tags

**Steps**:

1. Run Stage 1 with a first version (e.g., `v1.0.0`)
2. Verify changelog includes README.md content for initial release
3. Complete Stages 2 and 3
4. Verify all stages work correctly without previous tag reference

## Validation Checklist

After running the tests, verify the following:

### File Changes
- [ ] `src/web/package.json` version updated correctly
- [ ] `src/cook-web/package.json` version updated correctly
- [ ] `docker/docker-compose.prod.yml` image tags updated
- [ ] Version changes committed to repository

### GitHub Release
- [ ] Release created with correct tag
- [ ] Changelog content is accurate and well-formatted
- [ ] Release notes include proper sections (Features, Bug Fixes, etc.)
- [ ] Docker pull commands in release notes are correct
- [ ] Release is marked as "Latest release"

### Git Tags
- [ ] Annotated git tag created with correct name
- [ ] Tag points to correct commit
- [ ] Tag message is properly formatted

### Docker Images
- [ ] All three images built and pushed
- [ ] Version tags applied correctly
- [ ] Latest tags updated
- [ ] Multi-platform builds successful
- [ ] Image labels and metadata correct

### Workflow Logs
- [ ] All workflow steps completed successfully
- [ ] No unexpected warnings or errors
- [ ] Timing is reasonable (complete process < 30 minutes)

## Cleanup After Testing

After completing tests, clean up test resources:

1. **Delete Test Releases**
   ```bash
   # Delete release and tag via GitHub CLI
   gh release delete v0.0.1-test --yes
   git push origin --delete v0.0.1-test
   ```

2. **Revert Version Changes** (if needed)
   ```bash
   # Reset version files to previous state
   git revert <commit-hash-of-version-update>
   git push origin main
   ```

3. **Clean Docker Images** (optional)
   ```bash
   # Remove test images from registries if needed
   # This depends on your registry setup
   ```

## Troubleshooting Common Test Issues

### Workflow Permission Issues
- Ensure PAT_TOKEN has sufficient permissions
- Check repository settings for Actions permissions

### Environment Not Found
- Verify environment name matches exactly (`release`)
- Check environment configuration in repository settings

### Docker Build Failures
- Verify Docker registry credentials
- Check Dockerfile paths and build contexts
- Ensure secrets are properly configured

### Approval Gate Not Working
- Check environment configuration
- Verify required reviewers have proper access
- Ensure environment is referenced correctly in workflow

## Success Criteria

The three-stage release process is considered fully functional when:

- [ ] All test cases pass without manual intervention
- [ ] Error handling works correctly for invalid inputs
- [ ] Approval process functions as designed
- [ ] Docker images are built and deployed successfully
- [ ] Documentation is accurate and complete
- [ ] Team members can execute the process independently

## Performance Benchmarks

Target performance metrics:

- **Stage 1 (Prepare)**: < 5 minutes
- **Stage 2 (Publish)**: < 2 minutes (excluding approval time)
- **Stage 3 (Build)**: < 20 minutes for all images
- **Total Process**: < 30 minutes (excluding approval wait time)

## Next Steps After Successful Testing

1. **Team Training**: Share the process documentation with the team
2. **Production Use**: Start using for real releases
3. **Monitoring**: Set up monitoring for workflow success/failure
4. **Iteration**: Collect feedback and improve the process
5. **Legacy Cleanup**: Eventually remove the deprecated legacy workflow

---

**Note**: Always test in a safe environment first. Consider using a fork or test repository for initial validation before applying to production repositories.
