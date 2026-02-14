# Simplified Deployment Guide

**100% Free • No Custom Domain • Automated Deployment**

This guide covers the simplest possible deployment:
- **Frontend**: Vercel (free tier)
- **Backend**: Oracle Cloud Always Free VM
- **Connection**: Direct HTTP via public IP
- **CI/CD**: GitHub Actions (automated deployment)

**Total Cost: $0/month** ✅

---

## Architecture

```
User Browser
    ↓
Vercel Frontend (HTTPS) → https://your-app.vercel.app
    ↓
Oracle Cloud VM Backend (HTTP) → http://VM_PUBLIC_IP:8000
```

**Note**: Frontend is HTTPS (Vercel provides this), backend is HTTP (hobby project, no sensitive data).

---

## Prerequisites

- [ ] Oracle Cloud account (free, requires credit card verification)
- [ ] GitHub account (for repository and CI/CD)
- [ ] Vercel account (free)
- [ ] Valid email address (for Nominatim API)

**Time to deploy**: ~45-60 minutes (one-time setup)

---

## Part 1: Oracle Cloud VM Setup (~30-40 min)

### 1.1 Create Oracle Cloud Account

1. Go to https://www.oracle.com/cloud/free/
2. Click **Start for free**
3. Complete signup (requires credit card for verification - won't be charged)
4. Verify your account via email

### 1.2 Create Compute Instance

1. Log in to Oracle Cloud Console
2. Navigate to **☰ Menu** → **Compute** → **Instances**
3. Click **Create Instance**

**Configure instance:**

| Setting | Value | Notes |
|---------|-------|-------|
| **Name** | `travelbook-backend` | Any name you want |
| **Compartment** | (root) | Default is fine |
| **Placement** | Choose any AD | Doesn't matter for hobby project |
| **Image** | Ubuntu 22.04 Minimal | Or latest Ubuntu LTS |
| **Shape** | **AMD**: VM.Standard.E2.1.Micro (1 OCPU, 1GB RAM)<br>**OR**<br>**ARM**: VM.Standard.A1.Flex (up to 4 OCPUs, 24GB RAM) | Both are Always Free |
| **Virtual Network** | Create new VCN | Default settings |
| **Subnet** | Create public subnet | Default settings |
| **Public IP** | ✅ Assign public IPv4 address | **REQUIRED** |
| **SSH Keys** | Generate or upload | Save the private key! |

4. Click **Create**
5. Wait 1-2 minutes for provisioning
6. **Note the Public IP Address** (you'll need this!)

### 1.3 Configure Security List (Firewall Rules)

1. On the instance details page, click the **Subnet** name
2. Click **Default Security List**
3. Click **Add Ingress Rules**

Add these 3 rules:

**Rule 1: SSH**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: TCP
- Destination Port: `22`
- Description: SSH access

**Rule 2: HTTP (optional, for future)**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: TCP
- Destination Port: `80`
- Description: HTTP

**Rule 3: Backend API**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: TCP
- Destination Port: `8000`
- Description: TravelBook API

Click **Add Ingress Rules**

### 1.4 Connect to VM

```bash
# On your local machine
chmod 400 /path/to/ssh-key-XXXX.key

ssh -i /path/to/ssh-key-XXXX.key ubuntu@YOUR_VM_PUBLIC_IP
```

You should now be connected to your Oracle VM!

### 1.5 Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose

# Log out and back in for group changes
exit

# SSH back in
ssh -i /path/to/ssh-key-XXXX.key ubuntu@YOUR_VM_PUBLIC_IP
```

### 1.6 Configure UFW Firewall

```bash
# Allow necessary ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 8000/tcp    # Backend API

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### 1.7 Deploy Backend

```bash
# Install git
sudo apt install -y git

# Clone your repository (replace with your repo URL)
git clone https://github.com/YOUR_USERNAME/travel-book-generator.git
cd travel-book-generator/backend

# Create .env file
cp .env.example .env
nano .env
```

**Edit `.env` file:**
```bash
CONTACT_EMAIL=your-real-email@example.com
MOCK_GEOCODING=false
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app
```

Save and exit (`Ctrl+X`, `Y`, `Enter`)

**Deploy:**
```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

Wait for Docker to build and start. You should see:
```
✅ Backend is running!
```

**Test it:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

**Get your VM public IP:**
```bash
curl -4 ifconfig.me
# Note this IP - you'll need it for frontend!
```

---

## Part 2: Vercel Frontend Deployment (~10-15 min)

### 2.1 Push Code to GitHub

If you haven't already:

```bash
# On your local machine
cd travel-book-generator

# Initialize git (if needed)
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/travel-book-generator.git
git branch -M main
git push -u origin main
```

### 2.2 Deploy to Vercel

**Option A: Vercel Dashboard (Easiest)**

1. Go to https://vercel.com/
2. Sign up/Login (can use GitHub account)
3. Click **Add New...** → **Project**
4. Click **Import** next to your `travel-book-generator` repository
5. Configure project:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend` ← **IMPORTANT**
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
6. Click **Environment Variables** → **Add**
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `http://YOUR_VM_PUBLIC_IP:8000` (replace with actual IP)
   - **Environment**: Production
7. Click **Deploy**

Wait 2-3 minutes for deployment. You'll get a URL like:
`https://your-app.vercel.app`

**Option B: Vercel CLI**

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
cd frontend
vercel

# Follow prompts, then deploy to production
vercel --prod
```

Set environment variable:
```bash
vercel env add NEXT_PUBLIC_API_URL production
# Enter: http://YOUR_VM_PUBLIC_IP:8000
```

### 2.3 Update Backend CORS

SSH into your VM and update `.env`:

```bash
ssh -i /path/to/key ubuntu@YOUR_VM_PUBLIC_IP
cd ~/travel-book-generator/backend
nano .env
```

Update this line with your actual Vercel URL:
```bash
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app
```

Restart backend:
```bash
docker-compose restart
```

### 2.4 Test Full Stack

1. Visit your Vercel URL: `https://your-app.vercel.app`
2. Fill in a test trip
3. Generate PDF
4. Verify it works!

---

## Part 3: GitHub Actions CI/CD Setup (~15-20 min)

Set up automated deployment so you never have to manually deploy again!

See **[GITHUB_ACTIONS_SETUP.md](./GITHUB_ACTIONS_SETUP.md)** for detailed instructions.

**Quick summary:**

1. **Create SSH key for GitHub Actions**
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/github_actions_oracle -N ""
   ```

2. **Add public key to Oracle VM**
   ```bash
   ssh-copy-id -i ~/.ssh/github_actions_oracle.pub ubuntu@YOUR_VM_IP
   ```

3. **Add GitHub Secrets** (in repo Settings → Secrets):
   - `ORACLE_VM_HOST` = Your VM IP
   - `ORACLE_VM_USER` = `ubuntu`
   - `ORACLE_VM_SSH_KEY` = Contents of `~/.ssh/github_actions_oracle`
   - `VERCEL_TOKEN` = From https://vercel.com/account/tokens
   - `VERCEL_ORG_ID` = From `vercel link`
   - `VERCEL_PROJECT_ID` = From `vercel link`

4. **Push to main** - Automatic deployment! 🚀

---

## Maintenance

### Update Backend

**With GitHub Actions (automatic):**
```bash
cd backend
# Make changes
git add .
git commit -m "Update backend"
git push origin main
# Automatically deploys!
```

**Manual (if needed):**
```bash
ssh ubuntu@YOUR_VM_IP
cd ~/travel-book-generator
git pull
cd backend
docker-compose down
docker-compose build
docker-compose up -d
```

### Update Frontend

**With GitHub Actions (automatic):**
```bash
cd frontend
# Make changes
git add .
git commit -m "Update frontend"
git push origin main
# Automatically deploys!
```

### View Logs

```bash
ssh ubuntu@YOUR_VM_IP
cd ~/travel-book-generator/backend
docker-compose logs -f
```

### Backup Database

```bash
ssh ubuntu@YOUR_VM_IP
cd ~/travel-book-generator/backend
cp data/travelbook.db data/backup-$(date +%Y%m%d).db
```

---

## Troubleshooting

### Frontend can't connect to backend

**Check CORS settings:**
```bash
ssh ubuntu@YOUR_VM_IP
cd ~/travel-book-generator/backend
cat .env | grep ALLOWED_ORIGINS
# Should include your Vercel URL
```

**Check backend is running:**
```bash
ssh ubuntu@YOUR_VM_IP
curl http://localhost:8000/health
docker-compose ps
```

**Check Oracle security list allows port 8000**

### Backend not accessible from internet

1. Check Oracle Cloud security list (port 8000 open)
2. Check UFW: `sudo ufw status`
3. Check Docker: `docker-compose ps`
4. Test from VM: `curl http://localhost:8000/health`
5. Test from internet: `curl http://VM_IP:8000/health`

### PDF generation fails

```bash
ssh ubuntu@YOUR_VM_IP
cd ~/travel-book-generator/backend
docker-compose logs | grep -i error
```

Check memory:
```bash
free -h
# Should have at least 500MB available
```

### GitHub Actions deployment fails

- Check secrets are set correctly
- Check SSH key works: `ssh -i ~/.ssh/github_actions_oracle ubuntu@VM_IP`
- Check workflow logs in GitHub Actions tab
- See [GITHUB_ACTIONS_SETUP.md](./GITHUB_ACTIONS_SETUP.md) troubleshooting section

---

## Cost Summary

| Component | Cost |
|-----------|------|
| Oracle Cloud VM | **$0** (Always Free) |
| Vercel Hosting | **$0** (Free tier) |
| GitHub Actions | **$0** (Free for public repos) |
| **Total** | **$0/month** |

**Data limits:**
- Oracle VM: 10TB/month outbound (more than enough)
- Vercel: 100GB bandwidth/month (plenty for hobby project)
- GitHub Actions: Unlimited for public repos, 2000 min/month for private

---

## Security Notes

- ⚠️ Backend uses HTTP (not HTTPS) - fine for hobby project with no sensitive data
- ⚠️ Database is SQLite on VM - back up regularly
- ✅ Frontend has HTTPS (Vercel provides this automatically)
- ✅ No custom domain or SSL certificates needed
- ✅ Oracle Cloud provides basic DDoS protection

**For production with sensitive data**, you'd want:
- Custom domain with SSL/HTTPS for backend
- PostgreSQL instead of SQLite
- User authentication
- Rate limiting
- Regular backups

But for a hobby project, this setup is perfectly fine! 🎉

---

## Next Steps

- [ ] Complete Oracle Cloud VM setup
- [ ] Deploy backend to VM
- [ ] Deploy frontend to Vercel
- [ ] Set up GitHub Actions CI/CD
- [ ] Test full workflow
- [ ] Set up automated backups (optional)
- [ ] Add monitoring (optional)

---

## Quick Reference

**Backend URL:** `http://YOUR_VM_IP:8000`
**Frontend URL:** `https://your-app.vercel.app`
**API Docs:** `http://YOUR_VM_IP:8000/docs`

**SSH to VM:**
```bash
ssh -i /path/to/key ubuntu@YOUR_VM_IP
```

**Restart Backend:**
```bash
cd ~/travel-book-generator/backend && docker-compose restart
```

**View Logs:**
```bash
cd ~/travel-book-generator/backend && docker-compose logs -f
```

---

**Happy deploying!** 🚀

For detailed CI/CD setup, see [GITHUB_ACTIONS_SETUP.md](./GITHUB_ACTIONS_SETUP.md)
