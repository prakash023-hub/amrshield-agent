# AMRShield — Setup Guide (Day 1 Commands)

## Prerequisites
- Python 3.11+
- Node.js 18+ (for Phoenix MCP server)
- Git
- Google Cloud SDK (`gcloud`)

---

## Step 1 — Clone & Virtual Environment

```bash
git clone https://github.com/YOUR_USERNAME/amrshield-agent.git
cd amrshield-agent

# Create venv
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows PowerShell)
# venv\Scripts\Activate.ps1
```

## Step 2 — Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 3 — Configure Environment

```bash
cp infrastructure/secrets_template.env .env
# Open .env and fill in your values:
# GCP_PROJECT_ID, PHOENIX_API_KEY, GEMINI_API_KEY
```

## Step 4 — GCP Authentication (macOS)

```bash
# Install gcloud if not done
brew install --cask google-cloud-sdk

# Login
gcloud auth login
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable APIs (one command)
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  generativelanguage.googleapis.com
```

## Step 5 — Start Phoenix Locally

```bash
# Terminal 1 — Phoenix UI (http://localhost:6006)
python -m phoenix.server.main serve

# Terminal 2 — Phoenix MCP server (for agents to query Phoenix)
npx -y @arizeai/phoenix-mcp@latest \
  --baseUrl http://localhost:6006 \
  --apiKey local-dev
```

## Step 6 — Test Gemini Connection

```bash
python -c "
import vertexai
from vertexai.generative_models import GenerativeModel
import os

vertexai.init(project=os.getenv('GCP_PROJECT_ID'), location='us-central1')
model = GenerativeModel('gemini-2.0-flash-001')
resp = model.generate_content('In one sentence: what is antimicrobial resistance?')
print(resp.text)
"
```

If you see a sentence about AMR — auth and quota are working. 🎉

## Step 7 — Run FastAPI Backend

```bash
# Terminal 3
uvicorn api.main:app --reload --port 8000

# Test it
curl http://localhost:8000/healthz
```

## Step 8 — Run All 4 Dashboards

```bash
# Terminal 4
streamlit run dashboards/clinician_console/app.py --server.port 8501

# Terminal 5
streamlit run dashboards/stewardship_admin/app.py --server.port 8502

# Terminal 6
streamlit run dashboards/surveillance_map/app.py --server.port 8503

# Terminal 7
streamlit run dashboards/audit_console/app.py --server.port 8504
```

## Step 9 — First Git Commit

```bash
git add .
git commit -m "chore: initial AMRShield scaffold with all 4 dashboards"
git remote add origin https://github.com/YOUR_USERNAME/amrshield-agent.git
git push -u origin main

# Tag when you submit
git tag v1.0-submission
git push --tags
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `429 error from Gemini` | Use `gemini-2.0-flash-001`, add retry with backoff |
| `Phoenix shows no traces` | Call `setup_phoenix()` BEFORE any agent is created |
| `Cloud Run cold start 10s` | Set `--min-instances 1` during demo recording |
| `gcloud auth error` | Run `gcloud auth application-default login` again |
| `MCP server can't connect` | Confirm `localhost:6006` loads in browser first |
| `Streamlit state reset` | Use `st.session_state["last_rec"]` to persist data |

---

## Cost Tips
- Use `gemini-2.0-flash-001` for Clinical + Prediction agents (10x cheaper)
- Use `gemini-2.0-pro` only for Self-Audit Agent (needs reasoning)
- Cloud Run with `min-instances=0` stays in free tier for demo traffic
- Set budget alerts at ₹500 / ₹1000 / ₹2000 in GCP Billing console
