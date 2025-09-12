# Universal Release Workflow Guide

This repository contains a **generic, reusable release workflow** that automatically detects your project type and handles version updates across multiple languages and frameworks.

## 🚀 **Supported Project Types**

### **Node.js / npm Projects**
- ✅ Automatically updates `package.json` files
- ✅ Supports monorepo structures
- ✅ Works with TypeScript, React, Next.js, etc.

### **Python Projects**
- ✅ `pyproject.toml` projects (modern Python packaging)
- ✅ `setup.py` legacy projects
- ✅ `__init__.py` with `__version__` variables
- ✅ Works with pip, Poetry, setuptools

### **Rust Projects**
- ✅ `Cargo.toml` version updates
- ✅ Support for workspaces

### **PHP Projects**
- ✅ `composer.json` version updates

### **Generic Projects**
- ✅ `VERSION`, `version.txt`, `.version` files
- ✅ `docker-compose.yml` image tag updates
- ✅ Custom version files

## 📋 **Prerequisites**

### **1. Commitizen Configuration (Recommended)**

Create one of these files in your project root:

**Option A: `cz.json`** (Simple)
```json
{
  "commitizen": {
    "name": "cz_conventional_commits",
    "tag_format": "v$major.$minor.$patch",
    "version_provider": "scm",
    "update_changelog_on_bump": true
  }
}
```

**Option B: `pyproject.toml`** (Python projects)
```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "v$major.$minor.$patch"
version_provider = "scm"
update_changelog_on_bump = true
```

### **2. Conventional Commits**

Use conventional commit messages for automatic changelog generation:
```
feat: add new user authentication
fix: resolve database connection timeout
docs: update API documentation
chore: update dependencies
```

## 🛠️ **Setup Instructions**

### **Step 1: Copy the Workflow**

Copy these files to your project:
```
.github/workflows/prepare-release.yml    # Main workflow
.github/workflows/build-on-release.yml   # Auto-build (optional)
```

### **Step 2: Configure GitHub Secrets (Optional)**

For automated publishing, add these secrets to your repository:
```
PAT_TOKEN          # Personal Access Token with repo permissions
DOCKERHUB_USER     # Docker Hub username (if using Docker)
DOCKERHUB_TOKEN    # Docker Hub access token (if using Docker)
```

### **Step 3: Customize Version File Detection**

The workflow automatically detects and updates version files. If you have custom files, you can:

1. **Add custom patterns** to the workflow
2. **Use standard file names** like `VERSION` or `version.txt`
3. **Follow conventional structures** (the workflow will find them)

## 🎯 **Usage**

### **Creating a Release**

1. **Trigger the workflow**:
   ```
   GitHub → Actions → "Prepare Release Draft" → Run workflow
   Input: v1.2.3
   ```

2. **Review the draft release** that gets created automatically

3. **Publish manually** through GitHub UI, or use the publish workflow

### **What Happens Automatically**

1. ✅ **Project detection**: Scans for different project types
2. ✅ **Version updates**: Updates all relevant version files
3. ✅ **Changelog generation**: Uses commitizen for professional changelogs
4. ✅ **Git commits**: Commits version changes to repository
5. ✅ **Draft release**: Creates GitHub release with installation instructions

## 📁 **Example Project Structures**

### **Node.js Monorepo**
```
project/
├── package.json              # ← Updated
├── packages/
│   ├── frontend/package.json # ← Updated
│   └── backend/package.json  # ← Updated
├── cz.json                   # ← Commitizen config
└── .github/workflows/        # ← Workflows
```

### **Python Library**
```
my-library/
├── pyproject.toml            # ← Updated & Commitizen config
├── src/
│   └── my_library/
│       └── __init__.py       # ← __version__ updated
└── .github/workflows/        # ← Workflows
```

### **Mixed Project**
```
full-stack-app/
├── package.json              # ← Frontend (Updated)
├── setup.py                  # ← Backend (Updated)
├── docker-compose.yml        # ← Docker tags (Updated)
├── VERSION                   # ← Generic version (Updated)
├── cz.json                   # ← Commitizen config
└── .github/workflows/        # ← Workflows
```

## 🔧 **Customization**

### **Adding Custom Version Files**

Edit the workflow to add your specific patterns:

```bash
# Add to the "Update project version files" step
if [ -f "my-custom-version.conf" ]; then
  echo "  → Updating my-custom-version.conf..."
  sed -i.bak "s/version=.*/version=$VERSION/" my-custom-version.conf
  rm -f my-custom-version.conf.bak
  UPDATED_FILES+=("my-custom-version.conf")
fi
```

### **Customizing Release Notes**

The workflow generates generic release notes. You can customize the template in the "Create GitHub Release Draft" step.

### **Docker Integration**

For Docker projects, the workflow automatically updates image tags in `docker-compose*.yml` files:
```yaml
# Before
image: myapp/frontend:v1.0.0

# After (automatically updated)
image: myapp/frontend:v1.2.3
```

## 🐛 **Troubleshooting**

### **"No version files found"**
- ✅ Normal for some project types
- ✅ Add a `VERSION` file if you want version tracking
- ✅ Use standard file names (`package.json`, `pyproject.toml`, etc.)

### **"Commitizen failed"**
- ✅ Workflow falls back to manual parsing
- ✅ Add `cz.json` for better changelog quality
- ✅ Check conventional commit format

### **"No changes detected"**
- ✅ Normal if no version files need updating
- ✅ Release will still be created with changelog

## 💡 **Best Practices**

1. **Use semantic versioning**: `v1.2.3` format
2. **Write conventional commits**: Enables automatic changelog categorization
3. **Test first**: Use patch releases (`v1.0.1`) for testing the workflow
4. **Review drafts**: Always review the generated draft release before publishing
5. **Backup approach**: Keep the old manual release process as backup

## 🔄 **Migration from Existing Workflows**

1. **Backup** your current `.github/workflows/`
2. **Copy** the new universal workflow files
3. **Test** with a patch version first
4. **Customize** any project-specific requirements
5. **Remove** old workflow files once confirmed working

---

## 📞 **Support**

This workflow is designed to be **copy-paste ready** for most projects. If you need customization:

1. Check the **inline comments** in the workflow files
2. Review **similar project examples** above
3. **Test incrementally** with patch releases
4. **Keep it simple** - the defaults work for 90% of projects

Happy releasing! 🚀
