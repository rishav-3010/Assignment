# Clara Answers - Zero-Cost Automation Pipeline

> Automated pipeline that converts demo call transcripts into Retell AI agent configurations (v1) and updates them using onboarding data (v2) — all at zero cost.

![Pipeline](https://img.shields.io/badge/Pipeline-Automated-6366f1) ![Cost](https://img.shields.io/badge/Cost-Zero-22c55e) ![Python](https://img.shields.io/badge/Python-3.10+-3776ab) ![n8n](https://img.shields.io/badge/n8n-Workflow-ff6d5a)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    CLARA ANSWERS PIPELINE                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐    │
│  │ Demo Call   │──▶│ Transcript   │───▶│ Account Memo     │    │
│  │ Transcript  │    │ Parser       │    │ Extractor (LLM)  │    │
│  └─────────────┘    └──────────────┘    └────────┬─────────┘    │
│                                                  │              │
│                                         ┌────────▼─────────┐    │
│  PIPELINE A (Demo → v1)                 │ Agent Spec       │    │
│                                         │ Generator        │    │
│                                         └────────┬─────────┘    │
│                                                  │              │
│                                         ┌────────▼─────────┐    │
│                                         │ Store v1 Outputs │    │
│                                         │ (JSON files)     │    │
│                                         └──────────────────┘    │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐    │
│  │ Onboarding  │──▶│ Update       │───▶│ Diff Engine      │    │
│  │ Transcript  │    │ Extractor    │    │ v1 → v2          │    │
│  └─────────────┘    └──────────────┘    └────────┬─────────┘    │
│                                                  │              │
│  PIPELINE B (Onboarding → v2)           ┌────────▼─────────┐    │
│                                         │ Store v2 +       │    │
│                                         │ Changelog        │    │
│                                         └──────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.10+
- Docker Desktop (optional, for n8n)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Gemini API key (free from https://aistudio.google.com/apikey)
# OR set LLM_MODE=rule_based to skip LLM entirely
```
### 3. Add Your Dataset

For testing, the `real_bens_electric_demo` transcripts are already placed in their respective folders. To process other accounts, place their transcript files in the `data/` directory following this structure:

```text
data/
├── demo/
│   ├── bens_electric_solutions/transcript.txt
│   ├── apex_fire_protection/transcript.txt
│   ├── pacific_hvac_services/transcript.txt
│   ├── guardian_alarm_systems/transcript.txt
│   └── summit_plumbing_mechanical/transcript.txt
└── onboarding/
    ├── bens_electric_solutions/transcript.txt
    ├── apex_fire_protection/transcript.txt
    ├── pacific_hvac_services/transcript.txt
    ├── guardian_alarm_systems/transcript.txt
    └── summit_plumbing_mechanical/transcript.txt
```

The pipeline supports multiple transcript formats automatically:
- **Zoom chat.txt** format (`HH:MM:SS From Speaker : message`)
- **Fireflies.ai** format (speaker lines with timestamps)
- **Plain text** transcripts (`Speaker: message`)

### 4. Run the Pipeline

There are three ways to run the pipeline:

**Option A: Batch Process All Transcripts (Recommended)**
This will process every folder inside `data/demo` and `data/onboarding`.
```bash
python -m scripts.batch_process
```

**Option B: Process a Single Account (End-to-End)**
If you want to run the entire pipeline (Demo -> v1 -> Onboarding -> v2 -> Dashboard) for just one account in a single command:
```bash
python -m scripts.run_account bens_electric_solutions
```

**Option C: Process Step-by-Step (Advanced)**
If you want to run the individual scripts one by one:

```bash
# 1. Pipeline A: Demo → v1
python -m scripts.extract_account_memo data/demo/bens_electric_solutions/transcript.txt
python -m scripts.generate_agent_spec bens_electric_solutions

# 2. Pipeline B: Onboarding → v2
python -m scripts.update_agent_from_onboarding data/onboarding/bens_electric_solutions/transcript.txt bens_electric_solutions

# 3. Export to Dashboard
python -m scripts.export_dashboard_data
```
> **Note:** Option A and Option B automatically export the data to the dashboard. Option C requires you to manually run the export command (step 3).

> **💡 Want to re-run the pipeline fresh?** Clear the cached LLM responses first:
> ```bash
> Remove-Item -Recurse -Force .cache
> ```

### 4. View Dashboard

Open `dashboard/index.html` in any browser. The dashboard includes:
- Account overview with metrics
- Memo viewer with structured data
- Agent spec viewer
- **Side-by-side diff viewer** (v1 → v2)
- Changelog with change reasons

### 5. Run via n8n (Optional)

```bash
docker compose up -d
# Open http://localhost:5678
# Import workflows from workflows/pipeline_a.json and pipeline_b.json
```

See [workflows/setup_guide.md](workflows/setup_guide.md) for detailed n8n setup.

---



## Output Structure

```
outputs/
├── batch_summary.json
└── accounts/
    └── <account_id>/
        ├── v1/
        │   ├── account_memo.json     # Structured account data from demo
        │   └── agent_spec.json       # Retell agent configuration
        └── v2/
            ├── account_memo.json     # Updated data from onboarding
            ├── agent_spec.json       # Updated agent configuration
            ├── changelog.md          # Human-readable changelog
            └── changelog.json        # Machine-readable changelog
```

## LLM Strategy (Zero-Cost)

| Mode | How It Works | When to Use |
|------|-------------|-------------|
| `gemini` | Google Gemini 2.5 Flash free tier (no credit card) | Best accuracy, ~50 req/day |
| `rule_based` | Regex + keyword extraction | Unlimited, no API needed |

The pipeline automatically falls back to rule-based extraction if the LLM is unavailable.

Responses are **cached** in `.cache/llm/` to avoid redundant API calls, making re-runs free.

## Retell Agent Setup

Since Retell doesn't offer free programmatic agent creation, the pipeline outputs an **Agent Draft Spec JSON** matching Retell's API schema.

To deploy in Retell:
1. Open [Retell Dashboard](https://www.retellai.com/)
2. Create a new agent
3. Copy the `system_prompt` from `agent_spec.json` into the agent's prompt field
4. Configure voice settings as specified in the spec
5. Set up call transfer numbers from the spec

## Known Limitations

1. **Audio transcription**: The pipeline expects text transcripts. Audio files require local Whisper transcription (not included to maintain zero-cost on all machines).
2. **Retell API**: Agent specs are generated as JSON files, not pushed to Retell programmatically (free tier limitation).
3. **LLM rate limits**: Gemini free tier allows ~50 requests/day. Batch processing 10 files uses ~20 requests (with caching).
4. **Rule-based fallback**: Less accurate than LLM extraction, may miss nuanced information.

## What I Would Improve with Production Access

- **Retell API integration**: Automatically create and update agents via Retell's API
- **Whisper integration**: Automatic audio-to-text transcription for call recordings
- **Webhook-triggered workflows**: Auto-process new calls as they come in
- **Database storage**: Supabase or PostgreSQL for proper persistence and querying
- **CI/CD pipeline**: Automated testing and deployment
- **Auth and multi-tenancy**: Secure access per client team
- **LLM fine-tuning**: Custom extraction model trained on Clara's specific data patterns

---

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `scripts/` | Python pipeline scripts |
| `scripts/utils/` | Shared utilities (LLM client, parser, schema, storage) |
| `templates/` | Prompt templates for extraction and agent generation |
| `data/` | Input transcript files |
| `outputs/` | Generated outputs (memos, specs, changelogs) |
| `workflows/` | n8n workflow exports + setup guide |
| `dashboard/` | Bonus web dashboard with diff viewer |

## License

Built for the ZenTrades AI / Clara Answers internship assignment. Not for public distribution.
