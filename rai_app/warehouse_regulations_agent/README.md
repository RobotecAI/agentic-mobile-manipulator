# Warehouse Safety Regulations RAG PoC

This instruction provides a step-by-step guide for running warehouse safety analysis using OSHA regulation documents and computer vision. The process involves scraping regulations, processing them, building a vector database, and running analysis.

## Workflow

### Install Dependencies

```bash
rai-config-init
```

### Step 1: Scrape OSHA Regulations (Data Collection)

Use the scrapper to download OSHA 29 CFR 1910 regulations:

```bash
python3 scrapper.py --output regulations
```

**Scrapper Options:**

Extra command-line flags to use when the scraper fails due to network, timing, or anti‑bot protections.

**scrapper.py**:

- `--output`: Output directory for scraped regulations (default: regulations)
- `--timeout`: Request timeout in seconds (default: 40)
- `--limit`: Process only first N URLs for debugging (default: 0 = no limit)
- `--force`: Ignore conditional GET; re-download all content
- `--sitemap-only`: Skip index fetch; rely solely on sitemap
- `--rotate-ua`: Rotate random browser user agent for each request
- `--debug`: Enable debug logging
- `--no-warmup`: Skip initial warm-up root request

The scrapper will:

- Download all OSHA 1910 regulations from the official website
- Save raw HTML, extracted text, and markdown versions
- Generate a manifest.json and manifest.csv for tracking
- Use conditional GET requests to avoid re-downloading unchanged content
- Download and rewrite image references to local paths

> [!NOTE]
> Images are saved to enable eventual switch to multimodal RAG to store more reach context. Currently, images are not used.

### Step 2: Process and Filter Regulations

Filter the scraped regulations to focus on warehouse-relevant sections and optionally summarize them:

```bash

python3 process_regulations.py --source regulations --dest processed_regulations --ranges "1-40,66-68,132-140,155-165,176,212,335"


python3 process_regulations.py --source regulations --dest processed_regulations --ranges "1-40,66-68,132-140,155-165,176,212,335" --summarize --model gpt-4o
```

> [!NOTE]
> Optional summarization was added to reduce context size of the retrieved info from vector database. Small LLMs seem to struggle with long context.

**Process Regulations Options:**

**process_regulations.py**:

- `--source, -s`: Source directory containing scraped regulations (default: regulations)
- `--dest, -d`: Destination directory for processed regulations (default: processed_regulations)
- `--ranges, -r`: Comma-separated ranges of regulation numbers (default: 1-40,66-68,132-140,155-165)
- `--list, -l`: List available regulations without copying
- `--summarize`: Enable AI summarization of regulations after copying
- `--model, -m`: Language model for summarization (default: gpt-4o)
- `--chain`: Summarization chain type - stuff, map_reduce, refine (default: stuff)
- `--chunk-size`: Character chunk size for splitting (default: 3500)
- `--chunk-overlap`: Character overlap between chunks (default: 300)
- `--short-threshold`: If source text shorter than this, keep as-is (default: 1200)
- `--overwrite-summaries`: Regenerate existing summaries
- `--verbose, -v`: Verbose logging

The default ranges focus on warehouse safety-relevant regulations:

- **1-40**: General safety standards, walking surfaces, exits
- **66-68**: Personal protective equipment basics
- **132-140**: Personal protective equipment details
- **155-165**: Respiratory protection, hearing protection
- **176**: Materials handling and storage
- **212**: General machinery safety
- **335**: Electrical safety

### Step 3: Build Vector Database

```bash
python3 build_vector_db.py --source processed_regulations --out regulations_db --model mxbai-embed-large
```

**Build Script Options:**

**build_vector_db.py** (original rag.py logic):

- `--source, -s`: Source directory containing regulation folders (default: processed_regulations)
- `--output, -o`: Output directory for FAISS vector database (default: regulations_db)
- `--strategy`: Document splitting strategy - per_regulation, recursive, markdown_headers (default: per_regulation)
- `--chunk-size`: Chunk size for text splitting (default: 1000)
- `--chunk-overlap`: Chunk overlap for text splitting (default: 200)
- `--embedding-model`: Ollama embedding model to use (default: mxbai-embed-large)
- `--test-query`: Optional test query to run after building the database

> [!NOTE]
> Per-regulation was chosen as the default split strategy because each OSHA section is already a coherent, self‑contained unit. Storing each regulation as one vector preserves context, simplifies traceability (easy citation), avoids over‑fragmentation, and still keeps chunks small enough for efficient retrieval.

### Step 3: Run RAG Agent

Run the image analysis agent with the pre-built vector database:

```bash
python3 rag.py --vector-db regulations_db --images-dir images
```

Options:

- `--vector-db, -d`: Path to the FAISS vector database directory (required)
- `--images-dir`: Path to the images dir to analyze (required)
- `--vision-model, -m`: Vision (multimodal) model used to inspect the image and list potential safety issues (default: qwen2.5vl:7b)
- `--final-output-model, -f`: (Optional) Alternative LLM for the final text assessment. If omitted, the vision model is reused.

> [!NOTE]
> You can use two different models: one vision-capable model to inspect the image and enumerate potential safety issues, and another (often stronger in pure text reasoning) text-only LLM to synthesize the final written analysis. This helps if the vision model is weaker at long context reasoning.

> [!NOTE]
> The documents are retrieved separately for each potential anomaly in the loop to overcome the hallucinations of small LLMs in processing long context.

## Example Usage

### Complete End-to-End Workflow

```bash
# Step 0: Scrape OSHA regulations (first time setup)
python3 scrapper.py --output regulations

# Step 1: Process and filter regulations (with optional summarization)
python3 process_regulations.py --source regulations --dest processed_regulations --ranges "1-40,66-68,132-140,155-165,176,212,335" --summarize

# Step 2: Build the vector database
python3 build_vector_db.py --source processed_regulations --out regulations_db

# Step 3: Run the safety analysis agent
python3 rag.py --vector-db regulations_db --images-dir images --vision-model LFM2-VL-3B-preview-251009-0235-2258
```
