# GitHub Actions CI/CD Setup Guide

This guide shows how to set up automated deployment using GitHub Actions.

---

## Overview

When you push to the `main` branch:
- **Backend changes** → Automatically deploy to Oracle Cloud VM via SSH
- **Frontend changes** → Automatically deploy to Vercel

**Cost: $0** (GitHub Actions is free for public repos, 2000 minutes/month for private repos)

---

## Part 1: Oracle Cloud VM Setup for CI/CD

### 1.1 Create SSH Key for GitHub Actions

On your **local machine**, generate a dedicated SSH key for GitHub Actions:

```bash
# Generate new SSH key (no passphrase for automation)
ssh-keygen -t ed25519 -f ~/.ssh/github_actions_oracle -N ""

# This creates two files:
# - ~/.ssh/github_actions_oracle (private key - for GitHub Secrets)
# - ~/.ssh/github_actions_oracle.pub (public key - for Oracle VM)
```

### 1.2 Add Public Key to Oracle VM

Copy the public key to your Oracle VM:

```bash
# Option 1: Using ssh-copy-id (easiest)
ssh-copy-id -i ~/.ssh/github_actions_oracle.pub ubuntu@YOUR_VM_IP

# Option 2: Manual method
cat ~/.ssh/github_actions_oracle.pub
# Copy the output, then SSH into your VM and add it to ~/.ssh/authorized_keys
```

Verify the key works:
```bash
ssh -i ~/.ssh/github_actions_oracle ubuntu@YOUR_VM_IP
# Should connect without password
exit
```

### 1.3 Initial VM Setup

SSH into your Oracle VM and set up the project:

```bash
ssh ubuntu@YOUR_VM_IP

# Install git if not already installed
sudo apt update
sudo apt install -y git

# Clone your repository
cd ~
git clone https://github.com/YOUR_USERNAME/travel-book-generator.git

# Set up the backend
cd travel-book-generator/backend

# Create .env file
cp .env.example .env
nano .env
# Edit CONTACT_EMAIL and ALLOWED_ORIGINS

# Deploy for the first time
./deploy.sh

# Verify it's running
curl http://localhost:8000/health
# Should return: {"status":"ok"}

# Note your VM's public IP
curl -4 ifconfig.me
```

### 1.4 Configure Git for Auto-Pull

On the Oracle VM, configure git to avoid issues with auto-pull:

```bash
cd ~/travel-book-generator

# Set git to use rebase strategy for pulls
git config pull.rebase false

# If you get "untracked files" errors, you can tell git to ignore them
git config --global user.email "github-actions@example.com"
git config --global user.name "GitHub Actions"
```

---

## Part 2: GitHub Repository Secrets Setup

You need to add secrets to your GitHub repository for the workflows to work.

### 2.1 Navigate to Repository Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

### 2.2 Add Backend Deployment Secrets

Add the following secrets:

#### `ORACLE_VM_HOST`
- **Value**: Your Oracle VM public IP address
- Example: `123.45.67.89`

```bash
# Get your VM IP
ssh ubuntu@YOUR_VM_IP "curl -4 ifconfig.me"
```

#### `ORACLE_VM_USER`
- **Value**: `ubuntu` (or whatever user you're using)

#### `ORACLE_VM_SSH_KEY`
- **Value**: Your private SSH key content
- Get it with:

```bash
cat ~/.ssh/github_actions_oracle
# Copy the ENTIRE output including:
# -----BEGIN OPENSSH PRIVATE KEY-----
# ... (key content) ...
# -----END OPENSSH PRIVATE KEY-----
```

### 2.3 Add Frontend Deployment Secrets

#### Get Vercel Tokens

1. Go to https://vercel.com/account/tokens
2. Create a new token named "GitHub Actions"
3. Copy the token

#### `VERCEL_TOKEN`
- **Value**: The token you just created

#### `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`

Deploy your frontend manually once to get these:

```bash
cd frontend

# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Link your project (follow prompts)
vercel link

# This creates a .vercel/project.json file
cat .vercel/project.json
```

Copy the values:
- **`VERCEL_ORG_ID`**: Value of `orgId` from the JSON
- **`VERCEL_PROJECT_ID`**: Value of `projectId` from the JSON

### 2.4 Verify All Secrets

You should have these 5 secrets configured:

| Secret Name | Example Value |
|-------------|---------------|
| `ORACLE_VM_HOST` | `123.45.67.89` |
| `ORACLE_VM_USER` | `ubuntu` |
| `ORACLE_VM_SSH_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `VERCEL_TOKEN` | `abc123...` |
| `VERCEL_ORG_ID` | `team_xxx...` |
| `VERCEL_PROJECT_ID` | `prj_xxx...` |

---

## Part 3: Testing the CI/CD Workflow

### 3.1 Test Backend Deployment

Make a change to the backend:

```bash
# On your local machine
cd backend/app

# Make a small change (e.g., update version in main.py)
# Then commit and push
git add .
git commit -m "Test backend deployment"
git push origin main
```

Watch the workflow:
1. Go to your GitHub repository
2. Click **Actions** tab
3. You should see "Deploy Backend to Oracle Cloud" running
4. Click on it to see logs

### 3.2 Test Frontend Deployment

Make a change to the frontend:

```bash
cd frontend/src/app

# Make a small change
git add .
git commit -m "Test frontend deployment"
git push origin main
```

Watch the workflow in the **Actions** tab.

### 3.3 Verify Deployment

After successful deployment:

```bash
# Check backend
curl http://YOUR_VM_IP:8000/health

# Check frontend
# Visit your Vercel URL (shown in workflow logs or Vercel dashboard)
```

---

## Part 4: Update Frontend API URL

After your backend is deployed, update the frontend to use the VM IP:

### 4.1 Set Vercel Environment Variable

1. Go to your Vercel project dashboard
2. Click **Settings** → **Environment Variables**
3. Add a new variable:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `http://YOUR_VM_IP:8000`
   - **Environment**: Production

4. Redeploy frontend:

```bash
cd frontend
git commit --allow-empty -m "Trigger redeploy"
git push origin main
```

---

## Part 5: Workflow Details

### Backend Workflow Triggers

The backend workflow runs when:
- You push to `main` branch AND
- Changes are in `backend/` directory OR
- Changes are in `.github/workflows/deploy-backend.yml`

You can also trigger it manually:
1. Go to **Actions** tab
2. Select "Deploy Backend to Oracle Cloud"
3. Click **Run workflow**

### Frontend Workflow Triggers

The frontend workflow runs when:
- You push to `main` branch AND
- Changes are in `frontend/` directory OR
- Changes are in `.github/workflows/deploy-frontend.yml`

Can also be triggered manually.

### What Happens During Deployment

**Backend:**
1. GitHub connects to your Oracle VM via SSH
2. Pulls latest code from git
3. Rebuilds Docker images
4. Restarts Docker Compose
5. Checks health endpoint
6. Reports success/failure

**Frontend:**
1. GitHub builds your Next.js app
2. Deploys to Vercel
3. Vercel automatically handles CDN distribution
4. Reports success/failure

---

## Troubleshooting

### Backend deployment fails with "Permission denied"

Check SSH key setup:
```bash
# Test SSH connection manually
ssh -i ~/.ssh/github_actions_oracle ubuntu@YOUR_VM_IP

# Check authorized_keys on VM
ssh ubuntu@YOUR_VM_IP "cat ~/.ssh/authorized_keys"
```

### Backend deployment fails with "git pull" errors

SSH into VM and fix git state:
```bash
ssh ubuntu@YOUR_VM_IP
cd ~/travel-book-generator

# Reset any local changes
git reset --hard origin/main

# Or if you have uncommitted changes you want to keep
git stash
git pull
git stash pop
```

### Frontend deployment fails with Vercel errors

Check Vercel secrets:
- Verify `VERCEL_TOKEN` is valid (tokens can expire)
- Verify `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` are correct
- Check Vercel dashboard for deployment logs

### Workflow doesn't trigger

Check workflow file paths:
- Ensure `.github/workflows/` directory exists
- Ensure YAML files have correct syntax
- Check the `paths` filter matches your changes

### Backend health check fails after deployment

SSH into VM and check logs:
```bash
ssh ubuntu@YOUR_VM_IP
cd ~/travel-book-generator/backend
docker-compose logs -f
```

---

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Use separate SSH keys** - Don't reuse your personal SSH key
3. **Rotate secrets periodically** - Update tokens every 6-12 months
4. **Monitor Actions logs** - Check for suspicious activity
5. **Use branch protection** - Require PR reviews before merging to `main`

---

## Optional Enhancements

### Add Slack Notifications

Add this step to your workflows to get notified:

```yaml
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Add Deployment Preview URLs

Frontend workflow already supports this - Vercel automatically creates preview deployments for PRs.

### Add Automated Tests

Before deploying, run tests:

```yaml
- name: Run tests
  run: |
    cd backend
    pytest
```

---

## Cost Summary

| Component | Cost |
|-----------|------|
| GitHub Actions (public repo) | **Free** (unlimited) |
| GitHub Actions (private repo) | **Free** (2000 min/month) |
| Oracle Cloud VM | **Free forever** |
| Vercel Deployment | **Free** (100 builds/month) |
| **Total** | **$0/month** |

---

## Next Steps

- [x] Set up SSH keys
- [x] Configure GitHub secrets
- [x] Test workflows
- [x] Update frontend API URL
- [ ] Set up branch protection (recommended)
- [ ] Add automated tests (optional)
- [ ] Configure notifications (optional)

---

**All set!** Your deployments are now fully automated. Just push to `main` and everything deploys automatically! 🚀
