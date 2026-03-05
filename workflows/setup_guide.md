# n8n Workflow Setup Guide

## Prerequisites
- Docker Desktop installed and running
- Project repository cloned locally
- Python 3.10+ installed (for running scripts)
- Gemini API key (optional, for LLM mode)

## Quick Start

### 1. Start n8n with Docker

```bash
# From the project root directory
docker compose up -d
```

n8n will be available at: **http://localhost:5678**

Default credentials:
- Username: `admin`
- Password: `claraadmin`

### 2. Import Workflows

1. Open n8n at http://localhost:5678
2. Go to **Workflows** → **Import from File**
3. Import `workflows/pipeline_a.json` (Demo → v1 Agent)
4. Import `workflows/pipeline_b.json` (Onboarding → v2 Agent)

### 3. Configure Input Parameters

In each workflow, click the **"Set Input Parameters"** node and update:
- `transcript_path`: Path to the transcript file (relative to `/data/datasets/`)
- `account_id`: The account identifier

### 4. Run Workflows

1. **Run Pipeline A first** for a demo transcript to generate v1 outputs
2. **Then run Pipeline B** for the corresponding onboarding transcript to generate v2

### 5. Batch Processing (Alternative)

Instead of n8n, you can run the batch processor directly:

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your Gemini API key (or set LLM_MODE=rule_based)

# Run batch process on all transcripts
python -m scripts.batch_process
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key (free tier) | - |
| `LLM_MODE` | `gemini` or `rule_based` | `gemini` |
| `GEMINI_MODEL` | Model to use | `gemini-2.5-flash-preview-05-20` |
| `GEMINI_RPM` | Max requests per minute | `10` |
| `GEMINI_RPD` | Max requests per day | `50` |

## Directory Mapping in Docker

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./data` | `/data/datasets` | Transcript files |
| `./outputs` | `/data/outputs` | Generated outputs |
| `./scripts` | `/data/scripts` | Python pipeline scripts |
| `./templates` | `/data/templates` | Prompt templates |

## Troubleshooting

- **n8n not starting**: Ensure Docker Desktop is running and port 5678 is free
- **Python scripts failing**: Make sure Python 3.10+ is available in the container or run scripts locally
- **LLM errors**: Check your Gemini API key or switch to `LLM_MODE=rule_based`
