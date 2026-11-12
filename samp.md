# AI Platform Handout — Pillars, Hosting, Tooling, RAG & Python Data

A readable study / onboarding handout. Keep the early database notes; the rest expands into the **five pillars of an AI application stack**, model hosting, GPUs, fine-tuning, and Python data tooling.

---

## Part 0 — Database landscape (quick map)

| Kind | Idea | Examples |
|------|------|----------|
| **RDS / structured** | First rung: tables, SQL, ACID | Postgres, MySQL, SQL Server |
| **Search** | Indexed, searchable, retrievable | Solr, Elasticsearch, OpenSearch, Redis Search, MongoDB Atlas Search |
| **Graph** | Nodes, edges, properties | Neo4j, JanusGraph, Amazon Neptune |
| **Time series** | Timestamped metrics/events | InfluxDB, Prometheus, TimescaleDB |
| **Document** | JSON/XML documents | MongoDB, Couchbase |
| **Key–value** | Simple K→V | Redis, DynamoDB, Cassandra (wide-column hybrid) |
| **Columnar** | Analytics / column layouts | Apache Arrow, Parquet + engines (DuckDB, Dremel-style) |
| **Vector** | Embeddings for similarity | Pinecone, Chroma, Weaviate, pgvector, Qdrant, Milvus |

These databases feed **RAG** (retrieval-augmented generation): chunks → embeddings → vector (and often keyword) search → LLM answer.

---

## Part 1 — The five pillars of an AI application stack

Think of production AI apps as five cooperating layers. You rarely skip one for long; you just start thin and deepen each pillar.

### Pillar 1 — AI model hosting

**What it is:** Where the weights live and how tokens are generated (inference). Also where you schedule **training / fine-tuning**.

**Why it matters:** Latency, cost, privacy (data never leaves your VPC), and which model sizes you can run (2B on a laptop vs 70B+ on multi-GPU).

**Typical options:**

- **Managed APIs:** OpenAI, Anthropic, Google, Azure OpenAI, AWS Bedrock, Vertex AI  
- **Self-host open weights:** vLLM, Hugging Face TGI, Ollama, llama.cpp, TensorRT-LLM, SGLang  
- **Platform ML:** SageMaker, Vertex AI endpoints, Azure ML, RunPod / Vast / Lambda for rentals  

**Outputs of this pillar:** An HTTP (or gRPC) **chat/completions** endpoint your tools can call.

---

### Pillar 2 — AI tooling (orchestration & agents)

**What it is:** Frameworks that turn “call an LLM” into workflows: prompts, tools, memory, multi-agent crews, graphs, retries.

**Core pieces people mean by “tooling”:**

| Tool | Role |
|------|------|
| **LangChain** | Chains, tools, retrievers, document loaders — glue for LLM apps |
| **LangGraph** | Stateful **graphs** of nodes/edges; cycles, checkpoints, human-in-the-loop |
| **OpenAI SDK** | Official client; chat, tools, Responses API; you can hand-roll a **ReAct** loop |
| **CrewAI** | Role-based **multi-agent crews** (researcher, writer, reviewer, …) |
| **LlamaIndex** | Strong RAG / indexing focus |
| **Haystack** | Pipelines for search + generation |

**ReAct loop (Reason + Act)** — pattern, not a product:

1. Model **reasons** (“I need weather”).  
2. Model **acts** (tool call: `browse_web`).  
3. Observation returns.  
4. Repeat until a final answer.  

OpenAI tool-calling, LangGraph `ToolNode`, and CrewAI tools all implement variants of this loop.

**Combining CrewAI + LangGraph (practical pattern):**

- Use **CrewAI** when the problem is “several specialists collaborating” (roles, tasks, sequential/hierarchical process).  
- Use **LangGraph** when you need **durable state**, branching, loops, approval gates, or one long-lived agent with checkpoints.  
- **Combine:**  
  - LangGraph node → invoke a CrewAI crew for a multi-role subtask; write results back into graph state; continue the graph.  
  - Or: CrewAI agent’s tool = “run this LangGraph workflow” for a complex deterministic subgraph (e.g. RAG → grade → rewrite).  
- Rule of thumb: **graph for control flow & persistence; crew for social/role division of labor.**

---

### Pillar 3 — AI gateway (e.g. LiteLLM)

**What it is:** A **single API façade** in front of many model providers. Apps talk OpenAI-compatible APIs; the gateway routes to OpenAI, Azure, Bedrock, vLLM, Anthropic, etc.

**LiteLLM (and peers like Portkey, Helicone, OpenRouter):**

- Unify chat/completions across providers  
- Keys, rate limits, fallbacks, load balancing  
- Spend tracking, logging, retries  
- Swap `gpt-4o-mini` ↔ local vLLM without rewriting every service  

**Why it matters:** Platform teams expose **one** internal “model URL”; product teams don’t hardcode five SDKs.

---

### Pillar 4 — MCP servers and MCP gateway

**MCP (Model Context Protocol):** Standard way for hosts (IDEs, agents, chat UIs) to discover and call **tools**, **resources**, and **prompts** exposed by **MCP servers**.

| Piece | Role |
|-------|------|
| **MCP server** | Implements tools (e.g. Frappe, GitHub, filesystem, browser). Speaks MCP over stdio/SSE/HTTP. |
| **MCP host / client** | Cursor, Claude Desktop, custom agent — connects to servers and lets the model call tools. |
| **MCP gateway** | Aggregates many MCP servers: auth, routing, allowlists, one endpoint for many backends (similar spirit to an API gateway). |

**Mental model:** MCP is “USB for tools.” LangChain/LangGraph tools and MCP tools can coexist; many stacks wrap MCP tools as LangChain tools or call them from a gateway.

---

### Pillar 5 — RAG, Hybrid RAG, and Markdown

**RAG (Retrieval-Augmented Generation):**

1. Ingest docs → chunk → **embed** → store in vector DB (and/or keyword index).  
2. At query time: embed question → retrieve top-k chunks → stuff into prompt → LLM answers **with citations**.  

**Hybrid RAG:** Combine **dense** (vector similarity) + **sparse** (BM25 / keyword). Often re-rank (cross-encoder / Cohere Rerank). Better for exact IDs, codes, names.

**Markdown in the pipeline:**

- Preferred intermediate for docs (headings = natural chunk boundaries).  
- Store `path`, `heading path`, `source URL` as metadata for citations.  
- Convert PDF/HTML → Markdown (or structured MDX) before chunking when possible.  
- Chat UIs often render assistant answers as Markdown.

**Related:** GraphRAG (entities/relations), multi-query retrieval, HyDE, agentic RAG (retrieve → grade → rewrite query).

---

## Part 2 — Hosting open LLMs (Mistral, DeepSeek, Qwen, Llama, Gemma, MoE, …)

### Model size intuition

| Size (approx) | Examples | Typical home |
|---------------|----------|--------------|
| **~1–4B** | Gemma 2B/4B, Phi small, TinyLlama | CPU / laptop GPU / T4 |
| **~7–14B** | Mistral 7B, Llama 8B, Qwen mid | Single consumer GPU or T4/L4 |
| **~27–34B** | Gemma 27B-class, Mid large dense | A10 / L40S / A100 40GB (quantize if needed) |
| **~70B+** | Llama 70B | Multi-GPU or heavy quantization |
| **MoE (e.g. ~8×7B active, large total)** | Mixtral-style, DeepSeek-MoE family | More VRAM for **total** params; compute follows **active** experts |
| **~30B-class dense** | “31B”-class checkpoints | Plan like large dense: A100/H100 or multi-GPU |

Exact names change often; treat sizes as **VRAM planning bands**, not marketing labels.

### How to host (open weights)

1. **Get weights** — Hugging Face Hub (`transformers` / `huggingface_hub`), or vendor packs. Respect licenses (Llama, Gemma, Qwen, Mistral each have terms).  
2. **Serve for inference** (pick one):  
   - **vLLM** — high-throughput OpenAI-compatible server (PagedAttention).  
   - **TGI (Text Generation Inference)** — HF production server.  
   - **Ollama / llama.cpp** — easy local / CPU-friendly GGUF.  
   - **SGLang / TensorRT-LLM** — performance-oriented.  
3. **Quantize** if VRAM is tight — AWQ, GPTQ, GGUF Q4/Q5/Q8, bitsandbytes 4/8-bit.  
4. **Put a gateway in front** — LiteLLM → your vLLM base URL.  
5. **Observe** — tokens/sec, queue depth, GPU util, OOM rates.

**MoE note:** Disk/VRAM for all experts can be large; runtime FLOPs track **activated** experts. Check the serving stack’s MoE support (vLLM supports many MoE architectures).

**DeepSeek / Qwen / Mistral / Llama / Gemma:** Same pattern — HF weights → vLLM/TGI/Ollama → OpenAI-compatible API → LangChain/LangGraph/LiteLLM.

---

## Part 3 — Hosting ML models from Hugging Face (CPU vs GPU + CUDA)

### CPU path

```text
pip install torch transformers accelerate
# device = "cpu"
model = AutoModelForSequenceClassification.from_pretrained("...")
inputs = tokenizer(text, return_tensors="pt")
outputs = model(**inputs)
```

- Good for: small classifiers, embeddings on modest traffic, prototyping.  
- Slow for large generative models. Prefer **onnxruntime**, **OpenVINO**, or **llama.cpp GGUF** for CPU LLM inference.

### GPU + CUDA path

1. Install **NVIDIA driver** + matching **CUDA toolkit** (or use NGC / cloud images).  
2. Install **PyTorch with CUDA** (`pip`/`conda` wheels that match CUDA 11.8 / 12.x).  
3. Verify: `torch.cuda.is_available()`, `nvidia-smi`.  
4. Load with `device_map="auto"` (Accelerate) or `.to("cuda")`.  
5. For LLMs prefer **vLLM/TGI** over raw `generate` loops in production.

**Useful HF ecosystem libs:** `transformers`, `datasets`, `accelerate`, `peft`, `bitsandbytes`, `sentence-transformers`, `diffusers` (images).

**Serving classic ML (sklearn, XGBoost):** joblib/pickle → FastAPI; or BentoML / MLflow / SageMaker. Separate from LLM serving, but same “model hosting” pillar.

---

## Part 4 — GPUs: inference vs training

| Role | GPUs | Notes |
|------|------|--------|
| **Inference** | **T4**, L4, A10, consumer RTX | T4 (16GB) is common cloud inference: good for 7B–13B quantized, embeddings, light MoE; watch VRAM. |
| **Training / fine-tuning** | **A100** (40/80GB), **H100** | High memory bandwidth & Tensor Cores; multi-GPU with FSDP/DeepSpeed ZeRO. H100 ≈ newer, faster for large training. |

**Rules of thumb:**

- Inference cares about **tokens/sec** and **batch concurrency**.  
- Training cares about **throughput of samples**, **gradient memory**, checkpoint I/O.  
- Fine-tune 7B with LoRA on a single A100 easily; full fine-tune 70B needs multi-GPU.  
- T4 can fine-tune tiny models / LoRA on small LLMs if sequences and batch are careful; prefer A100/H100 for serious SFT/DPO.

---

## Part 5 — LLM hosting & fine-tuning (end-to-end)

### Hosting checklist

1. Choose model + license.  
2. Choose precision (fp16 / bf16 / int8 / int4).  
3. Choose server (vLLM recommended for APIs).  
4. Autoscale workers; health checks; max context length.  
5. Gateway (LiteLLM) + auth + logging.  
6. App layer: LangGraph agent + RAG + MCP tools.

### Fine-tuning overview

| Method | Idea | When |
|--------|------|------|
| **Full fine-tune** | Update all weights | Max quality, expensive |
| **LoRA / QLoRA** | Small adapter matrices; QLoRA = LoRA on 4-bit base | Default for most teams |
| **SFT** | Supervised instruction pairs | Teach style / format / domain |
| **DPO / ORPO / RLHF** | Preference alignment | Helpfulness / safety / tone |
| **Continued pretrain** | More unlabeled domain text | Vocabulary / domain language |

**Pipeline:** curated dataset (JSONL) → `trl` / Axolotl / LLaMA-Factory / Unsloth → eval harness → merge adapters → deploy new revision behind gateway.

**Data quality > size.** Prefer clean, deduped, instruction-format examples with clear inputs/outputs.

---

## Part 6 — Python data handling (elaborate toolkit)

Use this as a “what exists in the Python data stack” map. You rarely need everything; you do need to know which tool owns which job.

### 6.1 Core tabular & arrays

| Library | Job |
|---------|-----|
| **pandas** | DataFrames: load CSV/Parquet/SQL, filter, groupby, join, reshape, time series basics |
| **NumPy** | n-dimensional arrays, linear algebra building block |
| **Polars** | Faster DataFrame alternative (Rust); lazy queries |
| **PyArrow** | Columnar in-memory; Parquet/Feather; bridge to Spark/DuckDB |
| **DuckDB** | In-process analytical SQL over files/DataFrames |

**Pandas habits that matter:**

- Prefer **Parquet** over CSV for large data.  
- Use `dtype` / categorical for memory.  
- Vectorize; avoid row-wise Python loops.  
- `merge`/`join` with explicit keys; watch cartesian explosions.  
- Time: `to_datetime`, `tz_localize`/`tz_convert`, `resample`.  
- Missing data: `isna`, `fillna`, `dropna` with intent.  
- Method chaining vs intermediate vars — be consistent and readable.  
- For >RAM data: chunk `read_csv`, or switch to Polars lazy / DuckDB / Spark / Dask.

### 6.2 I/O & storage

- **Files:** CSV, JSON/JSONL, Parquet, ORC, Avro, Excel (`openpyxl`), HDF5  
- **SQL:** `sqlalchemy` + pandas `read_sql` / `to_sql`; or SQLModel/Django ORM  
- **Cloud:** `s3fs`, `gcsfs`, `adlfs`; boto3 / azure-storage / google-cloud-storage  
- **Messages:** kafka-python / confluent-kafka; Redis  

### 6.3 Cleaning & validation

- **pandera** / **great_expectations** — schema & data quality tests  
- **pydantic** — validate records at API boundaries  
- Regex + `str` accessors in pandas for messy strings  
- Dedup: `drop_duplicates`, fuzzy (`rapidfuzz`)  

### 6.4 Statistics & classical ML

- **SciPy**, **statsmodels**  
- **scikit-learn** — preprocess, CV, metrics, pipelines  
- **XGBoost / LightGBM / CatBoost** — tabular boosting  
- **imbalanced-learn** — class imbalance  

### 6.5 Visualization & notebooks

- **Matplotlib**, **Seaborn**, **Plotly**  
- **Jupyter / Marimo** for exploration; promote stable code into modules/tests  

### 6.6 Scale-out

- **Dask** — parallel pandas-like  
- **Ray** — distributed Python / training  
- **PySpark** — cluster ETL  
- **Modin** — parallel pandas API (backends vary)  

### 6.7 NLP / embeddings / LLM data prep

- **datasets** (HF) — map/filter/shuffle large text corpora  
- **tiktoken** / HF tokenizers — count & truncate context  
- **sentence-transformers** — embedding models  
- Chunking: by tokens, headings (Markdown), or recursive character splitters (LangChain/LlamaIndex)  
- Store chunks + metadata for RAG  

### 6.8 Experiment & reproducibility

- **seed** NumPy/Torch/random  
- **logging** + structured JSON logs  
- **MLflow / W&B / Aim** — metrics & artifacts  
- Pin deps (`requirements.txt` / poetry / uv); lock CUDA builds carefully  

### 6.9 Minimal pandas cheat sheet

```python
import pandas as pd

df = pd.read_parquet("events.parquet")
df["ts"] = pd.to_datetime(df["ts"], utc=True)
df = df.loc[df["country"].eq("IN"), ["ts", "user_id", "amount"]]
daily = (
    df.set_index("ts")
      .groupby("user_id")
      .resample("D")["amount"]
      .sum()
      .reset_index()
)
daily.to_parquet("daily_user_amount.parquet", index=False)
```

---

## Part 7 — How the pillars fit one portal (like this repo)

Example mapping for a product chat:

1. **Hosting** — OpenAI `gpt-4o-mini` (or later vLLM for open models).  
2. **Tooling** — LangGraph agent (think → tools → answer); tools = summarize, generalize, `browse_web`.  
3. **Gateway** — optional LiteLLM if you add Azure/Bedrock/local later.  
4. **MCP** — optional: expose portal tools as MCP for Cursor/other hosts.  
5. **RAG** — optional next step: Markdown/docs → embeddings → hybrid retrieve into the same graph.  

**GPUs:** T4 for self-hosted inference experiments; A100/H100 when you fine-tune domain adapters.

---

## Part 8 — Glossary (short)

- **Inference** — run a trained model to get outputs.  
- **Training** — learn weights from data.  
- **Fine-tuning** — further train a pretrained model on your data.  
- **Embedding** — vector representation of text/image.  
- **Context window** — max tokens the model can see at once.  
- **Quantization** — store/compute weights in fewer bits.  
- **MoE** — Mixture of Experts; route tokens to specialist subnetworks.  
- **Tool / function calling** — model emits structured calls the runtime executes.  
- **Checkpoint** — saved model or LangGraph state snapshot.  

---

## Part 9 — Suggested learning order

1. Call one LLM API; then add one tool (ReAct).  
2. Add LangGraph state + checkpoint.  
3. Put LiteLLM in front when you have 2+ providers.  
4. Ingest Markdown → hybrid RAG.  
5. Self-host a small model (Gemma/Qwen 2–4B) on T4 via vLLM.  
6. LoRA fine-tune on A100; deploy adapter behind the gateway.  
7. Expose stable tools via MCP for IDE agents.  

---

*Handout for study and team onboarding. Model names and GPU SKUs evolve; verify current HF cards, licenses, and cloud instance catalogs before production.*
