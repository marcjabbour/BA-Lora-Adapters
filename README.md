# BA-LoRA-Adapters

A data pipeline for preparing customer-agent call transcripts for LoRA adapter training via Llama-Factory SFT (Supervised Fine-Tuning).

## Overview

This pipeline transforms raw call transcripts into high-quality training data by:
1. Cleaning and normalizing transcripts
2. Using LLM-based evaluation to identify and rewrite poor agent responses
3. Exporting to ShareGPT format for fine-tuning

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA PIPELINE ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │   Raw JSON   │      │  Sanitized   │      │   Tagged     │
    │  Transcripts │─────▶│  Transcripts │─────▶│  Transcripts │
    │              │      │              │      │  + Rewrites  │
    └──────────────┘      └──────────────┘      └──────────────┘
           │                     │                     │
           │                     │                     │
           ▼                     ▼                     ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │    Step 1    │      │    Step 2    │      │    Step 3    │
    │ Sanitization │      │   Tagging    │      │  Exporting   │
    │              │      │   (LLM)      │      │  (ShareGPT)  │
    └──────────────┘      └──────────────┘      └──────────────┘
                                                       │
                                                       ▼
                                                ┌──────────────┐
                                                │   ShareGPT   │
                                                │    Format    │
                                                │   (for SFT)  │
                                                └──────────────┘
                                                       │
                          ┌────────────────────────────┼────────────────────────────┐
                          │                            │                            │
                          ▼                            ▼                            ▼
                   ┌──────────────┐            ┌──────────────┐            ┌──────────────┐
                   │    Step 4    │            │ Llama-Factory│            │    Step 5    │
                   │   Training   │───────────▶│     SFT      │───────────▶│   Serving    │
                   │              │            │              │            │   (future)   │
                   └──────────────┘            └──────────────┘            └──────────────┘
```

## Pipeline Steps

### Step 1: Sanitization
Cleans raw call transcripts by:
- Filtering noise entries (`[noise]`, `<unk>`, empty strings)
- Mapping roles: `agent` → `assistant`, `caller` → `user`
- Merging consecutive same-speaker turns
- Assigning sequential turn counts

```bash
python scripts/sanitize_transcripts.py \
  --input data/raw/ \
  --output data/Step-1-Sanitization/output/
```

### Step 2: Tagging
Uses an LLM to evaluate each agent response:
- Assigns quality scores (1-10)
- Identifies issues (e.g., "abrupt", "unclear", "dismissive")
- Generates rewrites for responses scoring below threshold
- Creates conversation-level summaries

```bash
python scripts/tag_transcripts.py \
  --input data/Step-1-Sanitization/output/ \
  --output data/Step-2-Tagging/output/ \
  --provider openai
```

### Step 3: Exporting
Converts tagged transcripts to ShareGPT format:
- One training record per assistant turn
- Cumulative conversation history per record
- Uses rewritten responses when available

```bash
python scripts/export_to_sharegpt.py \
  --input data/Step-2-Tagging/output/ \
  --output data/Step-3-Exporting/output/
```

### Step 4: Training
Uses Llama-Factory for LoRA adapter training:
- Configurable training parameters (epochs, learning rate, batch size, etc.)
- Real-time training metrics via WebSocket
- Outputs trained LoRA adapter weights

```bash
python scripts/train_lora.py \
  --input data/Step-3-Exporting/output/ \
  --output data/Step-4-Training/output/
```

### Step 5: Serving (Future)
vLLM deployment for serving trained adapters.

## Project Structure

```
BA-LoRA-Adapters/
├── backend/                      # FastAPI backend for web UI
│   └── app/
│       ├── api/routes/           # API endpoints (pipeline, files, chat)
│       ├── core/                 # WebSocket & state management
│       ├── models/               # API data models
│       └── services/             # Pipeline executor, file handler
├── frontend/                     # React + Vite frontend
│   └── src/
│       ├── components/           # UI components (steps, pipeline, chat)
│       ├── hooks/                # Custom React hooks
│       ├── services/             # API client
│       └── store/                # Zustand state management
├── configs/
│   └── llm_config.yaml           # LLM provider settings
├── prompts/
│   └── tagging/
│       └── tagging_prompt.txt    # Prompt for LLM evaluation
├── data/
│   ├── raw/                      # Input transcripts
│   ├── Step-1-Sanitization/
│   ├── Step-2-Tagging/
│   ├── Step-3-Exporting/
│   ├── Step-4-Training/
│   └── Step-5-Serving/
├── src/
│   ├── models/                   # Pydantic data models (sanitized, tagged, sharegpt)
│   ├── llm/                      # LLM client abstraction
│   └── utils/                    # Logging utilities
├── scripts/
│   ├── sanitize_transcripts.py   # Step 1: Clean transcripts
│   ├── tag_transcripts.py        # Step 2: LLM quality tagging
│   ├── export_to_sharegpt.py     # Step 3: ShareGPT export
│   └── train_lora.py             # Step 4: LoRA training
├── start-backend.sh              # Backend startup script
└── start-frontend.sh             # Frontend startup script
```

## Setup

**Requirements:** Python 3.10 - 3.13 (some dependencies may not support Python 3.14+)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
```

## Usage

There are two ways to use this pipeline:

### Option 1: Web UI (Recommended)

The web UI provides a guided interface that orchestrates the entire pipeline with real-time progress tracking.

**Start the backend and frontend in separate terminals:**

```bash
# Terminal 1: Start the backend API server
./start-backend.sh
# Backend available at: http://localhost:8000
# API docs at: http://localhost:8000/docs

# Terminal 2: Start the frontend
./start-frontend.sh
# Frontend available at: http://localhost:5173
```

The UI walks you through each step, handles file uploads, and shows previews of the output at each stage.

### Option 2: CLI Scripts (Manual)

Run each pipeline step manually via command-line scripts. Place your raw transcript JSON files in `data/raw/` and run each step in sequence:

```bash
# Step 1: Sanitization
python scripts/sanitize_transcripts.py \
  --input data/raw/ \
  --output data/Step-1-Sanitization/output/

# Step 2: Tagging (requires OpenAI API key)
python scripts/tag_transcripts.py \
  --input data/Step-1-Sanitization/output/ \
  --output data/Step-2-Tagging/output/ \
  --provider openai

# Step 3: Export to ShareGPT format
python scripts/export_to_sharegpt.py \
  --input data/Step-2-Tagging/output/ \
  --output data/Step-3-Exporting/output/

# Step 4: Training with Llama-Factory
python scripts/train_lora.py \
  --input data/Step-3-Exporting/output/ \
  --output data/Step-4-Training/output/
```

You can also run any individual script independently if you have properly formatted input data. Use `--help` on any script to see all available options:

```bash
python scripts/sanitize_transcripts.py --help
```

## Data Models

See [src/models/](src/models/) for Pydantic schemas defining:
- **Sanitized Transcript**: Step 1 output
- **Tagged Transcript**: Step 2 output with quality scores and rewrites
- **ShareGPT Record**: Step 3 output for Llama-Factory SFT
