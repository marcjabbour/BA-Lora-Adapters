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
                   │   (future)   │            │              │            │    (vLLM)    │
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
│   ├── models/                   # Pydantic data models
│   ├── llm/                      # LLM client abstraction
│   └── utils/                    # Logging utilities
└── scripts/
    ├── sanitize_transcripts.py   # Step 1
    ├── tag_transcripts.py        # Step 2
    └── export_to_sharegpt.py     # Step 3
```

## Setup

**Requirements:** Python 3.10 - 3.13 (some dependencies may not support Python 3.14+)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
```

## Data Models

See [src/models/](src/models/) for Pydantic schemas defining:
- **Sanitized Transcript**: Step 1 output
- **Tagged Transcript**: Step 2 output with quality scores and rewrites
- **ShareGPT Record**: Step 3 output for Llama-Factory SFT
