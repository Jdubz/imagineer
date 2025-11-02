# Setup Version Bump Token

This guide explains how to configure a Personal Access Token (PAT) that allows the auto-version workflow to bypass branch protection rules and commit directly to `main`.

## Why This Is Needed

The `auto-version.yml` workflow automatically bumps the patch version after successful CI runs on `main`. However, the repository has branch protection rules requiring all changes to go through pull requests.

Since we don't want to manage PRs for automated version bumps, we need a token with permissions to bypass these rules.

## Setup Instructions

### 1. Create a Fine-Grained Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - Direct link: https://github.com/settings/tokens?type=beta

2. Click **"Generate new token"**

3. Configure the token:
   - **Token name**: `Imagineer Version Bump Token`
   - **Expiration**: `No expiration` (or set a long expiration like 1 year)
   - **Description**: `Allows auto-version workflow to bypass branch protection`
   - **Repository access**: `Only select repositories` → Select `Jdubz/imagineer`

4. Set **Repository permissions**:
   - **Contents**: `Read and write`
   - **Metadata**: `Read-only` (automatically selected)
   - **Workflows**: `Read and write` (needed to trigger subsequent workflows)

5. Expand **"Repository permissions"** and ensure:
   - ✅ Contents: Read and write
   - ✅ Workflows: Read and write

6. Click **"Generate token"** at the bottom

7. **IMPORTANT**: Copy the token immediately - you won't be able to see it again!
   - The token will start with `github_pat_`

### 2. Add Token to Repository Secrets

1. Go to your repository: https://github.com/Jdubz/imagineer

2. Navigate to **Settings → Secrets and variables → Actions**
   - Direct link: https://github.com/Jdubz/imagineer/settings/secrets/actions

3. Click **"New repository secret"**

4. Configure the secret:
   - **Name**: `VERSION_BUMP_TOKEN` (exactly this name - it's used in the workflow)
   - **Secret**: Paste the token you copied from step 1

5. Click **"Add secret"**

### 3. Configure Branch Protection Bypass (Important!)

The token alone isn't enough - you also need to add it to the bypass list in branch protection:

1. Go to repository **Settings → Rules → Rulesets**
   - Direct link: https://github.com/Jdubz/imagineer/rules

2. Find and click on the ruleset that protects `main` (likely named something like "Require PR for main")

3. Click **"Edit"** on the ruleset

4. Scroll down to **"Bypass list"**

5. Click **"Add bypass"**

6. Select **"Repository admin"** or add your GitHub username to the bypass list
   - **Important**: The token inherits your permissions, so if you (the token owner) are in the bypass list, the token can bypass the rules

7. Click **"Save changes"**

**Alternative approach** (if the above doesn't work):
- Create a GitHub App instead of a PAT (more complex but more granular permissions)
- Add the app to the bypass list

### 4. Verify the Setup

After adding the secret, the next time the auto-version workflow runs (after a successful CI run on `main`), it should be able to push directly to `main` without creating a PR.

You can manually trigger a test by:
1. Merging a PR to `main`
2. Waiting for CI to complete successfully
3. Checking the auto-version workflow runs: https://github.com/Jdubz/imagineer/actions/workflows/auto-version.yml

## Troubleshooting

### Token still can't push to main

If you see errors like:
```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Changes must be made through a pull request.
```

This means the bypass isn't configured correctly. Double-check:
1. The token has `Contents: Read and write` permission
2. You (the token owner) are in the bypass list for the branch protection ruleset
3. The secret is named exactly `VERSION_BUMP_TOKEN`

### Workflow doesn't run at all

Make sure:
1. The workflow condition is met: CI completed successfully on `main`
2. The actor isn't `github-actions[bot]` (to prevent infinite loops)

### Token expired

If using an expiring token:
1. Generate a new token following steps above
2. Update the `VERSION_BUMP_TOKEN` secret with the new value

## Security Considerations

- The token has write access to your repository, so keep it secure
- Only the auto-version workflow uses this token
- The workflow only commits version bumps (no code changes)
- Consider using a shorter expiration if you're concerned about long-lived tokens
- Regularly audit who has access to repository secrets

## Workflow Configuration

The workflow has been updated to use this token in two places:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    ref: main
    token: ${{ secrets.VERSION_BUMP_TOKEN || secrets.GITHUB_TOKEN }}

- name: Push version commit
  env:
    GITHUB_TOKEN: ${{ secrets.VERSION_BUMP_TOKEN || secrets.GITHUB_TOKEN }}
  run: |
    git push origin HEAD:main
```

The `|| secrets.GITHUB_TOKEN` fallback ensures the workflow doesn't break if the token isn't configured (though it won't bypass branch protection).
