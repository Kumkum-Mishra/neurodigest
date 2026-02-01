# NeuroDigest - Vercel Deployment Guide

यह guide आपको NeuroDigest project को Vercel के free tier पर deploy करने में मदद करेगा।

## Prerequisites

1. GitHub account
2. Vercel account (free tier available)
3. Project को GitHub पर push करें

## Step 1: GitHub पर Project Push करें

```bash
# अगर Git repository initialize नहीं है
git init
git add .
git commit -m "Initial commit for Vercel deployment"
git branch -M main

# GitHub पर नया repository बनाएं और push करें
git remote add origin https://github.com/yourusername/neurodigest.git
git push -u origin main
```

## Step 2: Vercel Postgres Database Setup

1. Vercel Dashboard में जाएं: https://vercel.com/dashboard
2. **Storage** tab पर click करें
3. **Create Database** → **Postgres** select करें
4. Free tier के लिए **Hobby** plan select करें
5. Database का नाम दें (e.g., `neurodigest-db`)
6. Database create होने के बाद, **.env.local** tab में connection string copy करें

## Step 3: Vercel Project Deploy करें

### Option A: Vercel CLI के साथ

```bash
# Vercel CLI install करें
npm i -g vercel

# Project directory में जाएं
cd neurodigest

# Login करें
vercel login

# Deploy करें
vercel

# Production deploy के लिए
vercel --prod
```

### Option B: Vercel Dashboard के साथ

1. Vercel Dashboard में जाएं: https://vercel.com/dashboard
2. **Add New Project** click करें
3. GitHub repository select करें
4. Project settings:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (default)
   - **Build Command**: (leave empty)
   - **Output Directory**: (leave empty)
5. **Environment Variables** add करें:
   - `DATABASE_URL` - Vercel Postgres connection string
   - `JWT_SECRET_KEY` - एक strong random string (generate करने के लिए: `openssl rand -hex 32`)
   - `GROQ_API_KEY` - (optional) आपका Groq API key
   - अन्य optional variables DEPLOY.md file में देखें

## Step 4: Environment Variables Setup

Vercel Dashboard में जाकर **Settings** → **Environment Variables** में निम्नलिखित add करें:

### Required:
- `DATABASE_URL`: Vercel Postgres connection string
- `JWT_SECRET_KEY`: JWT tokens के लिए secret key (strong random string - generate करने के लिए: `openssl rand -hex 32`)

### Recommended:
- `GROQ_API_KEY`: LLM features के लिए (optional)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time in minutes (default: 60)

### Optional:
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`: Email functionality के लिए
- `DIGEST_FRESHNESS_SECONDS`: Digest freshness time (default: 3600)

## Step 5: Database Migration

Deploy के बाद, database tables automatically create हो जाएंगी क्योंकि `init_db()` function startup पर run होता है।

अगर manual migration चाहिए:

```bash
# Local में run करें (database URL Vercel Postgres के साथ set करें)
python -c "from storage.db import init_db; init_db()"
```

## Step 6: Verify Deployment

1. Vercel Dashboard में **Deployments** tab check करें
2. Deploy successful होने के बाद, **Visit** button पर click करें
3. Frontend page open होनी चाहिए
4. API endpoints test करें:
   - `https://your-project.vercel.app/api/digest` - Digest endpoint
   - `https://your-project.vercel.app/docs` - FastAPI documentation

## Important Notes

### Serverless Limitations:

1. **Scheduler**: `apscheduler` serverless functions में काम नहीं करता। Scheduled tasks के लिए:
   - Vercel Cron Jobs use करें (free tier में available)
   - या external cron service (e.g., cron-job.org) use करें जो `/api/trigger` endpoint को call करे

2. **Database**: SQLite file-based database serverless में काम नहीं करेगा। Vercel Postgres use करना जरूरी है।

3. **File Storage**: Local file storage (जैसे `storage/archive/`) serverless में persist नहीं होगा। Cloud storage (S3, Vercel Blob) use करें।

4. **Cold Starts**: Serverless functions में cold start हो सकता है (first request slow हो सकता है)।

### Vercel Cron Jobs Setup (Optional):

अगर daily digest automatically generate करना चाहते हैं:

1. `vercel.json` में cron job add करें:

```json
{
  "crons": [{
    "path": "/api/trigger",
    "schedule": "0 9 * * *"
  }]
}
```

2. यह हर दिन 9 AM पर `/api/trigger` endpoint को call करेगा।

## Troubleshooting

### Database Connection Issues:
- Vercel Postgres connection string सही है या नहीं check करें
- Environment variable `DATABASE_URL` properly set है या नहीं verify करें

### Build Errors:
- `requirements.txt` में सभी dependencies हैं या नहीं check करें
- Large dependencies (जैसे `torch`, `transformers`) build time बढ़ा सकते हैं

### API Errors:
- Vercel function logs check करें: **Deployments** → **Function Logs**
- Local में test करें: `python -m uvicorn mcp_server.main:app --reload`

### CORS Issues:
- Frontend और backend same domain पर हैं, तो CORS issue नहीं होना चाहिए
- अगर different domains use कर रहे हैं, `mcp_server/main.py` में CORS origins update करें

## Project Structure for Vercel

```
neurodigest/
├── api/
│   └── index.py          # Vercel serverless function wrapper
├── public/
│   └── index.html        # Frontend
├── mcp_server/           # FastAPI backend
├── services/             # Business logic
├── storage/              # Database models
├── fetchers/             # Content fetchers
├── vercel.json           # Vercel configuration
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variables template
```

## Support

अगर कोई issue आए:
1. Vercel function logs check करें
2. Local में test करें
3. GitHub Issues में report करें

Happy Deploying! 🚀
