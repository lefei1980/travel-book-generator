# Quick Reference Guide

**100% Free Deployment • No Domain Required • Automated CI/CD**

---

## 📖 Documentation Map

| File | When to Read | Time |
|------|--------------|------|
| **DEPLOYMENT_SUMMARY.md** | Start here - overview | 5 min |
| **DEPLOYMENT.md** | Ready to deploy | 45-60 min |
| **GITHUB_ACTIONS_SETUP.md** | Setting up automation | 20 min |
| **QUICKSTART.md** | Running locally first | 5 min |
| **CLAUDE.md** | Understanding architecture | 10 min |
| **TODO.md** | Checking status/next steps | 2 min |

---

## 🚀 Deployment Steps

### Quick Overview (1 hour total)

```bash
# 1. Oracle Cloud VM (~30-40 min)
# - Create account
# - Create VM
# - Configure firewall
# - Deploy backend

# 2. Vercel (~10-15 min)
# - Push to GitHub
# - Import to Vercel
# - Set environment variable

# 3. Connect (~5 min)
# - Update CORS
# - Test

# 4. CI/CD (~15-20 min)
# - Setup SSH keys
# - Add GitHub secrets
# - Done!
```

**Detailed guide**: `DEPLOYMENT.md`

---

## 💻 Local Development

### Start Everything Locally

```bash
# Terminal 1: Backend
cd backend
docker-compose up

# Terminal 2: Frontend
cd frontend
npm install
npm run dev

# Visit: http://localhost:3000
```

**Detailed guide**: `QUICKSTART.md`

---

## 🔧 Common Commands

### Backend (Oracle VM)

```bash
# SSH into VM
ssh -i /path/to/key ubuntu@YOUR_VM_IP

# View logs
cd ~/travel-book-generator/backend
docker-compose logs -f

# Restart
docker-compose restart

# Stop
docker-compose down

# Rebuild and restart
docker-compose down && docker-compose build && docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Frontend (Vercel)

```bash
# Deploy manually
cd frontend
vercel --prod

# View logs
vercel logs

# List deployments
vercel ls
```

### GitHub Actions

```bash
# Trigger backend deployment
git add backend/
git commit -m "Update backend"
git push origin main

# Trigger frontend deployment
git add frontend/
git commit -m "Update frontend"
git push origin main

# View workflow status
# Go to: https://github.com/YOUR_USERNAME/travel-book-generator/actions
```

---

## 🌐 Your URLs

After deployment:

| Service | URL | Notes |
|---------|-----|-------|
| **Frontend** | `https://your-app.vercel.app` | HTTPS ✅ |
| **Backend API** | `http://YOUR_VM_IP:8000` | HTTP only |
| **API Docs** | `http://YOUR_VM_IP:8000/docs` | Swagger UI |
| **GitHub Actions** | `github.com/YOUR_USERNAME/travel-book-generator/actions` | CI/CD status |
| **Vercel Dashboard** | `vercel.com/dashboard` | Deployment logs |

---

## 🔑 GitHub Secrets Needed

For CI/CD automation, add these in: `Settings → Secrets → Actions`

| Secret | Value | How to Get |
|--------|-------|------------|
| `ORACLE_VM_HOST` | `123.45.67.89` | Your VM public IP |
| `ORACLE_VM_USER` | `ubuntu` | Default user |
| `ORACLE_VM_SSH_KEY` | `-----BEGIN...` | `cat ~/.ssh/github_actions_oracle` |
| `VERCEL_TOKEN` | `xxx...` | https://vercel.com/account/tokens |
| `VERCEL_ORG_ID` | `team_xxx` | From `vercel link` |
| `VERCEL_PROJECT_ID` | `prj_xxx` | From `vercel link` |

**Setup guide**: `GITHUB_ACTIONS_SETUP.md`

---

## 📁 Important Files

### Configuration Files

```
backend/
├── .env                      # Your secrets (NOT in git)
├── .env.example              # Template for .env
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Service orchestration
└── deploy.sh                 # Deployment script

frontend/
├── .env.local                # Local dev API URL
├── .env.example              # Template
└── vercel.json               # Vercel config

.github/workflows/
├── deploy-backend.yml        # Auto-deploy backend
└── deploy-frontend.yml       # Auto-deploy frontend
```

### Documentation Files

```
DEPLOYMENT_SUMMARY.md         # Start here
DEPLOYMENT.md                 # Full deployment guide
GITHUB_ACTIONS_SETUP.md       # CI/CD setup
QUICKSTART.md                 # Local development
CLAUDE.md                     # Architecture docs
TODO.md                       # Current status
QUICK_REFERENCE.md            # This file
```

---

## 🔥 Troubleshooting Quick Fixes

### Frontend can't connect to backend

```bash
# Check backend is running
ssh ubuntu@VM_IP "curl http://localhost:8000/health"

# Check CORS settings
ssh ubuntu@VM_IP "cat ~/travel-book-generator/backend/.env | grep ALLOWED"

# Should include your Vercel URL
```

### Backend not accessible

```bash
# Check firewall
ssh ubuntu@VM_IP "sudo ufw status"

# Check Docker
ssh ubuntu@VM_IP "cd ~/travel-book-generator/backend && docker-compose ps"

# Restart
ssh ubuntu@VM_IP "cd ~/travel-book-generator/backend && docker-compose restart"
```

### GitHub Actions fails

```bash
# Test SSH manually
ssh -i ~/.ssh/github_actions_oracle ubuntu@VM_IP

# Check secrets in: GitHub repo → Settings → Secrets → Actions
```

**Full troubleshooting**: See respective guide's troubleshooting section

---

## 💰 Cost Breakdown

| Service | Monthly Cost | Limits |
|---------|--------------|--------|
| Oracle Cloud VM | **$0** | Always Free (forever) |
| Vercel | **$0** | 100GB bandwidth |
| GitHub Actions | **$0** | Unlimited (public repo) |
| **Total** | **$0** | ✅ |

**No credit card charges. No surprises.** 🎉

---

## ⏱️ Time Estimates

| Task | First Time | After Experience |
|------|------------|------------------|
| Oracle VM setup | 30-40 min | 15 min |
| Vercel deployment | 10-15 min | 5 min |
| GitHub Actions setup | 15-20 min | 10 min |
| **Total initial setup** | **1 hour** | **30 min** |
| Updates (with CI/CD) | **30 sec** | **30 sec** |

---

## 🎯 Next Steps

Choose your path:

### Path 1: Deploy Now ✅
1. Read `DEPLOYMENT_SUMMARY.md` (5 min)
2. Follow `DEPLOYMENT.md` (1 hour)
3. Set up `GITHUB_ACTIONS_SETUP.md` (20 min)
4. Done!

### Path 2: Test First 🧪
1. Follow `QUICKSTART.md` (5 min)
2. Test locally
3. Then deploy (Path 1)

### Path 3: Learn More 📚
1. Read `CLAUDE.md` for architecture
2. Explore code
3. Then deploy (Path 1)

---

## 📞 Support Resources

- **Deployment issues**: `DEPLOYMENT.md` → Troubleshooting
- **CI/CD issues**: `GITHUB_ACTIONS_SETUP.md` → Troubleshooting
- **Local dev issues**: `QUICKSTART.md`
- **Architecture questions**: `CLAUDE.md`
- **Current status**: `TODO.md`

---

## ✨ Features

What users can do:
1. **Enter trip details** - Title, dates, daily itinerary
2. **Add places** - Hotels, attractions, restaurants
3. **Generate PDF** - With maps, routes, images, descriptions
4. **Download** - Professional travel guide ready to print

What you get:
- ✅ Geocoding (Nominatim)
- ✅ Route calculation (OSRM)
- ✅ Wikipedia descriptions
- ✅ Wikimedia Commons images
- ✅ Interactive maps (Leaflet)
- ✅ Professional PDF output

---

**Ready to deploy?** Start with `DEPLOYMENT_SUMMARY.md`! 🚀
