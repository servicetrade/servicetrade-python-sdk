# GitHub Secrets Configuration

This document describes the GitHub secrets required for the CI/CD pipelines of the ServiceTrade Python SDK.

## Required Secrets

### `PYPI_API_TOKEN`

**Purpose:** Used to authenticate with PyPI when publishing the package.

**Required for:** Publishing workflow (`.github/workflows/publish.yml`)

**How to obtain:**
1. Log in to [PyPI](https://pypi.org) (or create an account if you don't have one)
2. Go to Account Settings → API tokens
3. Click "Add API token"
4. Choose a token name (e.g., "servicetrade-python-sdk-github-actions")
5. Set the scope to "Entire account" (for new projects) or limit to this specific project once published
6. Click "Create token"
7. Copy the token (starts with `pypi-`)

**How to add to GitHub:**
1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `PYPI_API_TOKEN`
5. Value: Paste the token from PyPI
6. Click "Add secret"

**Security notes:**
- This token allows publishing packages to PyPI under your account
- Treat it as a password - never commit it to code
- Consider using a scoped token limited to this project after first publish

---

### `CODECOV_TOKEN` (Optional)

**Purpose:** Used to upload code coverage reports to Codecov for tracking test coverage over time.

**Required for:** CI workflow (`.github/workflows/ci.yml`) - coverage upload step

**How to obtain:**
1. Log in to [Codecov](https://codecov.io) using your GitHub account
2. Add your repository to Codecov
3. Go to your repository settings in Codecov
4. Copy the "Repository Upload Token"

**How to add to GitHub:**
1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `CODECOV_TOKEN`
5. Value: Paste the token from Codecov
6. Click "Add secret"

**Security notes:**
- This token is optional - the CI will still pass without it
- Coverage reports are helpful for tracking test quality over time
- The upload step is configured to not fail the CI if the token is missing

---

## Environment Configuration

The publish workflow uses a GitHub Environment called `release` for additional protection:

### Setting up the `release` Environment

1. Go to your repository on GitHub
2. Navigate to Settings → Environments
3. Click "New environment"
4. Name: `release`
5. Configure protection rules (recommended):
   - **Required reviewers:** Add team members who must approve releases
   - **Wait timer:** Optional delay before deployment proceeds
   - **Deployment branches:** Limit to tags matching `v*`

This ensures that package publishing only happens after explicit approval.

---

## Secrets Summary Table

| Secret Name | Required | Used By | Purpose |
|------------|----------|---------|---------|
| `PYPI_API_TOKEN` | Yes | `publish.yml` | Authenticate with PyPI for package publishing |
| `CODECOV_TOKEN` | No | `ci.yml` | Upload coverage reports to Codecov |

---

## Trusted Publishing Alternative (Recommended)

Instead of using `PYPI_API_TOKEN`, you can configure PyPI Trusted Publishing which uses OpenID Connect (OIDC) for more secure, tokenless authentication.

### Setting up Trusted Publishing:

1. Log in to [PyPI](https://pypi.org)
2. Go to your project → Manage → Publishing
3. Add a new "trusted publisher":
   - **Owner:** Your GitHub organization or username
   - **Repository name:** `servicetrade-python-sdk`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `release` (optional but recommended)

4. Update `.github/workflows/publish.yml` to remove the `password` line:

```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  # No password needed with trusted publishing
```

**Benefits of Trusted Publishing:**
- No long-lived tokens to manage or rotate
- More secure - uses short-lived OIDC tokens
- Easier to set up and maintain
- No risk of token exposure

---

## First-Time Setup Checklist

- [ ] Create PyPI account (if needed)
- [ ] Generate PyPI API token
- [ ] Add `PYPI_API_TOKEN` to GitHub repository secrets
- [ ] (Optional) Create Codecov account and add `CODECOV_TOKEN`
- [ ] (Optional) Create `release` environment with protection rules
- [ ] (Recommended) Configure Trusted Publishing on PyPI after first release

---

## Troubleshooting

### "Invalid API token" error during publish
- Verify the token is correctly copied (no extra whitespace)
- Ensure the token has not been revoked
- Check if the token scope includes this package

### Coverage upload fails
- The `CODECOV_TOKEN` secret may be missing
- This is non-blocking - the CI will still pass
- Add the token if you want coverage tracking

### Publish workflow not triggering
- Ensure you pushed a tag matching `v*` pattern (e.g., `v1.0.0`)
- Use: `git tag v1.0.0 && git push origin v1.0.0`
