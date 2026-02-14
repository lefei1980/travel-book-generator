# Quick Start Guide

Get TravelBook Generator running in 5 minutes locally, or follow the full deployment guide for production.

---

## Local Development (5 minutes)

### Prerequisites
- Node.js 18+
- Python 3.11+
- Docker (optional, recommended)

### Backend (Option 1: Docker - Recommended)

```bash
cd backend

# Copy and configure environment
cp .env.example .env
# Edit .env with your email for CONTACT_EMAIL

# Run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Backend (Option 2: Without Docker)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy and configure environment
cp .env.example .env
# Edit .env with your email for CONTACT_EMAIL

# Create directories
mkdir -p data output

# Run backend
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
# Default points to http://localhost:8000 - no changes needed

# Run development server
npm run dev
```

### Access the App

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Production Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete production deployment guide using:
- Oracle Cloud Always Free (backend)
- Cloudflare DNS Proxy
- Vercel (frontend)

**Total cost: ~$10-15/year (domain name only)**

---

## Testing the App

1. Visit http://localhost:3000
2. Enter a trip:
   - **Title**: "Paris Weekend"
   - **Start Date**: Any future date
   - **Add some places**:
     - Day 1: Hotel (Eiffel Tower Hotel), Attraction (Louvre Museum)
     - Day 2: Restaurant (Le Jules Verne), Attraction (Arc de Triomphe)
3. Click **Generate Travel Guide**
4. Wait for processing (~30-60 seconds)
5. Download your PDF!

---

## Troubleshooting

### Backend won't start
- **Docker**: Check `docker-compose logs`
- **Python**: Ensure Python 3.11+ and all dependencies installed
- **Port conflict**: Make sure port 8000 is available

### Frontend can't connect to backend
- Verify backend is running: `curl http://localhost:8000/health`
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Check CORS settings in `backend/.env`

### PDF generation fails
- Check backend logs for Playwright errors
- Ensure Playwright browsers installed: `playwright install chromium`
- Verify sufficient memory available (~500MB needed)

### Mock data for testing
Set `MOCK_GEOCODING=true` in `backend/.env` to bypass Nominatim rate limits during testing.

---

## Project Structure

```
travel-book-generator/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI app
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   └── templates/      # Jinja2 HTML templates
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js app router
│   │   ├── components/    # React components
│   │   └── lib/           # API client
│   └── package.json
├── DEPLOYMENT.md          # Full deployment guide
├── QUICKSTART.md          # This file
└── CLAUDE.md             # Project documentation
```

---

## Next Steps

- ✅ Get it running locally (you are here!)
- 📖 Read [CLAUDE.md](./CLAUDE.md) for architecture details
- 🚀 Deploy to production: [DEPLOYMENT.md](./DEPLOYMENT.md)
- 🎨 Customize PDF templates in `backend/app/templates/`
- 🗺️ Enhance maps and routing logic
- 📊 Add analytics and monitoring

---

**Happy traveling!** 🌍✈️
