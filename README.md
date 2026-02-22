# PaperMind

A self-hosted research mentor that ingests academic PDFs, builds a knowledge graph, and provides two AI chat agents to help you deeply understand papers.

## Why

Signal-to-noise in research is worsening. Reading papers is a skill most people never formally develop. PaperMind gives you a personal tutor and examiner for every paper you read — so you actually learn, not just skim.

## What it does

- **Upload a PDF** — the LLM reads the full paper and extracts title, authors, abstract, a detailed summary, key concepts, and concept relationships
- **Knowledge graph** — concepts link across papers in a force-directed graph, colored by your confidence level
- **Teach agent** — a patient mentor who explains concepts, draws connections, and meets you at your level
- **Zealot agent** — a Socratic examiner who asks hard questions, resists giving answers, and pushes for real understanding
- **Swap freely** — both agents share one conversation per paper, with color-coded messages, so you can learn and test in the same session
- **Knowledge tracking** — after Zealot sessions, the LLM assesses your understanding of each concept on a 0–1 confidence scale
- **Personal takeaways** — write notes on each paper; they're shown in chat context so the agents know what you've taken away

## Stack

Python, NiceGUI, LiteLLM, SQLite, ECharts. No heavyweight frameworks, no external databases.

## Setup

```bash
git clone https://github.com/aaryan-dharmadhikari/paper-mind.git
cd paper-mind
cp .env.example .env
```

Edit `.env` with your LLM provider credentials:

```
LITELLM_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk-...
```

Any [LiteLLM-supported provider](https://docs.litellm.ai/docs/providers) works — OpenAI, Anthropic, Gemini, local models, etc. The model must support PDF/document input.

## Run

```bash
./run.sh
```

This creates a virtualenv, installs dependencies, and starts the app at [http://localhost:8080](http://localhost:8080).

## Usage

1. Go to **Upload** and drop in a PDF
2. Wait for the LLM to parse it (takes 10–30s depending on provider)
3. Read the summary on the **Paper Detail** page, add your own takeaways
4. Click **Open Chat** to start a conversation
5. Use the **Teach/Zealot toggle** to switch agents mid-conversation
6. Hit **Assess** after a Zealot session to update your confidence scores
7. Check the **Dashboard** for an overview of papers, concepts, and knowledge gaps
8. Explore the **Graph** to see how concepts connect across papers
