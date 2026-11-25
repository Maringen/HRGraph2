# HR Temporal Knowledge Graph

This project implements a production-grade HR Knowledge Management system using Graphiti, FalkorDB, and CocoIndex for ingesting unstructured HR data into a temporally-aware knowledge graph.

## Technologies

- **Graphiti-core**: Temporal knowledge graph framework
- **FalkorDB**: Graph database backend
- **CocoIndex**: Incremental data pipelines for ingestion
- **FastAPI**: API layer for queries
- **Sigma.js**: Custom frontend for graph visualization
- **GPT-4o/Claude 3.5 Sonnet**: LLM for processing

## Quick start (Docker)

The whole stack (FalkorDB + web UI + API) runs with one command:

```bash
cp .env.example .env      # then fill in OPENAI_API_KEY / ANTHROPIC_API_KEY
docker compose up -d --build
```

| Service          | URL                     |
| ---------------- | ----------------------- |
| API / dashboard  | http://localhost:5000   |
| FalkorDB Browser | http://localhost:3001   |
| FalkorDB (Redis) | localhost:6379          |
| FalkorDB (Bolt)  | localhost:7687          |

Useful commands:

```bash
docker compose logs -f app     # follow API logs
docker compose ps              # service status
docker compose down            # stop (add -v to wipe graph data)
```

## Setup (local, without Docker)

1. Start infrastructure:
   ```bash
   docker compose up -d falkordb falkordb-browser
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env`:
   ```
   FALKORDB_HOST=localhost
   FALKORDB_PORT=6379
   GRAPHITI_DB_URL=sqlite:///graphiti.db
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

4. Place HR documents (.pdf, .md) in `./hr_vault`

5. Run ingestion:
   ```bash
   python data_ingestion.py
   ```

6. Start API server:
   ```bash
   python main.py
   ```

7. Access the dashboard at http://localhost:5000 or externally at http://vps-97995726.vps.ovh.net:5000/

## Features

- Incremental ingestion of HR data from files
- Temporal knowledge graph tracking state changes
- Hybrid search (semantic + graph traversal)
- Employee career history queries
- MCP integration for Claude Desktop

## API Endpoints

- `POST /query`: Hybrid search query
- `GET /history/{employee_name}`: Chronological career narrative

## MCP Integration

Copy `claude_desktop_config.json` to Claude Desktop config directory.