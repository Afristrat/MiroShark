# Models

Four independent model slots (see [Configuration](CONFIGURATION.md#model-slots) for the env vars). This doc covers which models to put in which slot.

## Cloud presets (OpenRouter)

Two benchmarked presets ship in `.env.example`. Copy one and set your API key.

Each slot controls a different quality axis:

| Slot | Controls | Key finding |
|---|---|---|
| **Default** | Persona richness, sim density | Haiku produces distinct 348-char voices; cheaper models produce generic 170-char copy |
| **Smart** | Report quality (#1 lever) | Claude Sonnet 9/10, cheaper alternatives 2–5/10 on prior benchmark runs |
| **NER** | Extraction reliability | Needs deterministic JSON — pick a model that doesn't silently emit CoT |
| **Wonderwall** | Cost (biggest consumer) | 850+ calls, 7M+ tokens. Verbosity matters more than $/M |

### Cheap mode — ~$1/run, ~10 min

Qwen3.5 Flash + DeepSeek V3.2 + Grok-4.1 Fast. Reasoning is disabled on every slot (`LLM_DISABLE_REASONING=true` sends `reasoning: {enabled: false}` in `extra_body`), which is the difference between a ~45s scenario-suggest call and a ~3s one.

| Slot | Model | $/M (in/out) | Observed avg latency |
|---|---|---|---|
| Default | `qwen/qwen3.5-flash-02-23` | $0.065 / $0.26 | 8.5s (Wonderwall-heavy prompts) |
| Smart | `deepseek/deepseek-v3.2` | $0.252 / $0.378 | 12.5s (report ReACT loops) |
| NER | `x-ai/grok-4.1-fast` | $0.20 / $0.50 | 2.0s |
| Wonderwall | `qwen/qwen3.5-flash-02-23` | $0.065 / $0.26 | 7.6s (per agent action) |

Observed on a 359-call end-to-end run (2.99M tokens, ~67 min wall clock): **~$0.50 total** including Grok-`:online` web enrichment. Docs without public figures typically come in under $0.30.

### Best mode — ~$3.50/run, ~25 min

Claude reports, Haiku personas, cheap Wonderwall. Best report quality at reasonable cost.

| Slot | Model | $/M | Why |
|---|---|---|---|
| Default | `anthropic/claude-haiku-4.5` | $0.80/$4.00 | Rich personas, dense sim configs |
| Smart | `anthropic/claude-sonnet-4.6` | $3.00/$15.00 | 9/10 report quality, only ~19 calls |
| NER | `x-ai/grok-4.1-fast` | ~$0.20 | Stable JSON with reasoning off |
| Wonderwall | `qwen/qwen3.5-flash-02-23` | ~$0.10 | Wonderwall doesn't drive quality — Smart does |

> Bassira's Cheap and Best presets both use `qwen3-emb-8b` on DGX-2 (`http://192.168.100.7:8005`), with its native 4,096 dimensions. This keeps the Neo4j vector indexes and every retrieval path on one embedding space.
>
> **Latency note** — every OpenRouter call goes through `LLMClient`, which injects `reasoning: {enabled: false}` into `extra_body` by default. Turn it off with `LLM_DISABLE_REASONING=false` only if a specific slot benefits from chain-of-thought (rare for MiroShark's structured prompts).

## Local mode (Ollama)

> **Context override required.** Ollama defaults to 4096 tokens, but MiroShark prompts need 10–30k. Create a custom Modelfile:
>
> ```bash
> printf 'FROM qwen3:14b\nPARAMETER num_ctx 32768' > Modelfile
> ollama create mirosharkai -f Modelfile
> ```

| Model | VRAM | Speed | Notes |
|---|---|---|---|
| `qwen2.5:32b` | 20GB+ | ~40 t/s | Default in `.env.example` — solid all-rounder |
| `qwen3:30b-a3b` *(MoE)* | 18GB | ~110 t/s | Fastest — MoE activates only 3B params per token |
| `qwen3:14b` | 12GB | ~60 t/s | Good balance for mid-range GPUs |
| `qwen3:8b` | 8GB | ~42 t/s | Minimum viable; drop Wonderwall rounds if context is tight |

### Hardware quick-pick

| Setup | Model |
|---|---|
| RTX 3090/4090 or M2 Pro 32GB+ | `qwen2.5:32b` |
| RTX 4080 / M2 Pro 16GB | `qwen3:30b-a3b` |
| RTX 4070 / M1 Pro | `qwen3:14b` |
| 8GB VRAM / laptop | `qwen3:8b` |

**Embeddings for Bassira:** Qwen3-emb-8b is served by DGX-2 through its OpenAI-compatible endpoint and returns 4,096 dimensions. An Ollama embedding model may be used only in a separate standalone deployment with a correspondingly rebuilt Neo4j vector index; it is not compatible with Bassira's production graph.

## Hybrid mode

Most users land here naturally: run local for the high-volume simulation rounds, route to Claude for reports.

```bash
LLM_MODEL_NAME=qwen2.5:32b
SMART_PROVIDER=claude-code
SMART_MODEL_NAME=claude-sonnet-4-20250514
```
