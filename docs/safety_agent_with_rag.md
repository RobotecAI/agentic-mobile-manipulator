# Warehouse Safety Agent with RAG

This instruction provides a step-by-step guide for running warehouse safety analysis using OSHA regulation documents and computer vision. The process involves scraping regulations, processing them, building a vector database, and running analysis.

## Data preparation and testing

### Step 1: Scrape OSHA Regulations (Data Collection)

Use the scrapper to download OSHA 29 CFR 1910 regulations:

```bash
uv run rai_app/warehouse_regulations_agent/scrapper.py --output regulations
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
> Images are saved to enable eventual switch to multimodal RAG to store more rich context. Currently, images are not used.

### Step 2: Process and Filter Regulations

Filter the scraped regulations to focus on warehouse-relevant sections and optionally summarize them:

```bash

uv run rai_app/warehouse_regulations_agent/process_regulations.py --source regulations --dest processed_regulations --ranges "1-40,66-68,132-140,155-165,176,212,335"


uv run rai_app/warehouse_regulations_agent/process_regulations.py --source regulations --dest processed_regulations --ranges "1-40,66-68,132-140,155-165,176,212,335" --summarize --model gpt-4o
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
uv run rai_app/warehouse_regulations_agent/build_vector_db.py --source processed_regulations --out regulations_db
```

**Build Script Options:**

**build_vector_db.py** (original rag.py logic):

- `--source, -s`: Source directory containing regulation folders (default: processed_regulations)
- `--output, -o`: Output directory for FAISS vector database (default: regulations_db)
- `--strategy`: Document splitting strategy - per_regulation, recursive, markdown_headers (default: recursive)
- `--chunk-size`: Chunk size for text splitting (default: 2048)
- `--chunk-overlap`: Chunk overlap for text splitting (default: 256)
- `--test-query`: Optional test query to run after building the database

> [!NOTE] > `Recurisive` was chosen as the default split strategy to limit the size of a single document (some regulations are thousands of tokens in length), to prevent the injection of irrelevant excerpts into the context of the model, and to simplify the process of determining relevancy of passages.

### Step 4: (Optional) Test the performance of the Warehouse Safety Agent

Run the image analysis agent with the pre-built vector database to test the performance and behavior of the Warehouse Safety Agent on selected images:

```bash
uv run rai_app/warehouse_regulations_agent/rag.py --vector-db regulations_db --images-dir images
```

Options:

- `--vector-db, -d`: Path to the FAISS vector database directory (required)
- `--images-dir`: Path to the images dir to analyze (required)
- `-k`: (Optional) Number of nearest neighbors to retrieve from the vector database (default: 10)

> [!NOTE]
> The documents are retrieved separately for each potential anomaly in the loop to overcome the hallucinations of small LLMs in processing long context.

## Example Usage

### Data preparation and testing

```bash
# Step 1: Scrape OSHA regulations (first time setup)
uv run rai_app/warehouse_regulations_agent/scrapper.py --output regulations

# Step 2: Process and filter regulations
uv run rai_app/warehouse_regulations_agent/process_regulations.py --source regulations --dest processed_regulations --ranges "1-40,66-68,132-140,155-165,176,212,335"

# Step 3: Build the vector database
uv run rai_app/warehouse_regulations_agent/build_vector_db.py --source processed_regulations --out regulations_db

# Step 4: (Optional) Test the performance of the Warehouse Safety Agent
uv run rai_app/warehouse_regulations_agent/rag.py --vector-db regulations_db --images-dir images
```

### Running the Warehouse Safety Agent inside the Demo

1. Start O3DE and the ROS 2 stack as described in ["Running the Demo"](./running.md)
2. In a new terminal, start the Warehouse Safety Agent:

```bash
bash scripts/start_safety_agent.sh
```
