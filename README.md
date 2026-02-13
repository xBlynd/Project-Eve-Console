# EVE Project Console

**Evolution - Your AI Operations Intelligence Layer**

Built by Ian Martin for xsvStudio, LLC

## Overview

EVE Project Console is a local web dashboard that lets you register project folders ("Libraries"), index their contents, and query them using your local EVE AI models (Construction Director and CTO personas) powered by Ollama + Mistral.

## Features

- **Library Management**: Register project folders like Allstar bid documents, Ghost Shell code, client specs
- **Dual Personas**: 
  - EVE-CD (Construction Director) for bid analysis, RFP review, contract management
  - EVE-DEV (CTO/Engineer) for code review, architecture, debugging
- **Local & Offline**: 100% local execution, no cloud dependencies
- **File-Aware**: Reads relevant files from registered libraries to provide context-aware answers
- **xsvStudio Branded**: Custom UI with midnight blue, coral, and white theme

## Tech Stack

- **Backend**: FastAPI (Python)
- **AI**: Ollama with eve-cd and eve-dev models
- **Storage**: SQLite
- **Frontend**: HTML/CSS/JavaScript
- **Deployment**: 100% local on Windows/Mac/Linux

## Installation

### Prerequisites

1. **Python 3.10+**: [Download here](https://www.python.org/downloads/)
2. **Ollama**: [Download here](https://ollama.com/download)

### Setup Steps

1. **Clone the repository**:
```bash
git clone https://github.com/xBlynd/Project-Eve-Console.git
cd Project-Eve-Console
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Create EVE models in Ollama**:

First, download Mistral:
```bash
ollama pull mistral
```

Then create EVE-CD (Construction Director):
```bash
ollama create eve-cd -f models/EVE-CD.modelfile
```

And EVE-DEV (CTO/Engineer):
```bash
ollama create eve-dev -f models/EVE-DEV.modelfile
```

4. **Start the server**:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

5. **Open your browser**:
```
http://localhost:8000
```

## Usage

### Adding a Library

1. Click "Add Library" in the left sidebar
2. Enter a name (e.g., "Allstar Bid Standards")
3. Enter the full path to your folder
4. Select type: Project or Library
5. Click "Create"

### Indexing Files

1. Select a library from the list
2. Click "Index" button
3. Wait for the scan to complete (shows file count)

### Querying EVE

1. Select a library
2. Choose role: Construction Director or CTO/Engineer
3. Type your question
4. Click "Ask EVE"
5. View the answer with referenced files

## Project Structure

```
eve-console/
├── backend/
│   ├── main.py              # FastAPI app and routes
│   ├── models.py            # Pydantic data models
│   ├── database.py          # SQLite connection
│   └── services/
│       ├── indexer.py       # File scanning and indexing
│       ├── ollama_client.py # Ollama API integration
│       └── retriever.py     # File retrieval logic
├── frontend/
│   ├── index.html           # Main UI
│   ├── app.js               # API calls and interactions
│   └── styles.css           # xsvStudio theme
├── models/
│   ├── EVE-CD.modelfile     # Construction Director persona
│   └── EVE-DEV.modelfile    # CTO/Engineer persona
├── storage/
│   └── eve.db               # SQLite database (auto-created)
├── config.yaml              # Configuration
└── requirements.txt         # Python dependencies
```

## Configuration

Edit `config.yaml` to customize:

```yaml
ollama_base_url: "http://localhost:11434"
default_max_files: 10
default_max_chars: 20000
storage_path: "./storage/eve.db"
```

## What's Next

You now have a working local AI that:
- Reads YOUR files
- Speaks in YOUR voice (Construction Director vs CTO)
- Runs 100% offline with xsvStudio branding

For your demo tomorrow:
1. Add library: "Allstar Bid Standards" → point to your specs folder
2. Click "Index" → scans files in seconds
3. Ask: "What should be included in general conditions for a CM/GC project?"
4. Switch to Ghost Shell library + CTO role
5. Ask: "What files handle kernel boot sequence?"

## License

Proprietary - xsvStudio, LLC © 2026

## Support

For issues or questions: ian@xsvstudio.com
