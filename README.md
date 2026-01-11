# Doc QA - Document Question Answering System

A production-ready document analysis system that uses Google's Gemini AI models to generate comprehensive best-practice guidance reports from text documents. The system processes multiple documents in parallel, answering a predefined set of questions based solely on the document content.

## Features

- 🤖 **AI-Powered Analysis**: Leverages Google Gemini models (default: `gemini-2.5-flash`) via Google ADK for intelligent document analysis
- 📄 **Batch Processing**: Processes multiple documents concurrently with configurable parallelism
- 🎯 **Structured Output**: Generates well-formatted Markdown reports with consistent structure
- 🔒 **Document-Only Responses**: Strictly uses only the provided document content—no external knowledge or assumptions
- ⚡ **Async Processing**: High-performance async/await implementation for efficient document processing
- 📊 **Progress Tracking**: Visual progress bars for document and question processing

## Requirements

- Python >= 3.13
- Google ADK credentials configured
- Text documents in `.txt` format

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Doc_QA
```

2. Install dependencies using `uv` (recommended) or your preferred package manager:
```bash
uv sync
```

Alternatively, if using pip:
```bash
pip install -e .
```

3. Set up your environment variables (see [Configuration](#configuration) below)

## Configuration

Create a `.env` file in the project root with the following variables:

```env
# Google ADK Configuration
ADK_MODEL=gemini-2.5-flash  # Model to use for analysis

# Directory Configuration
DOCS_DIR=data                # Directory containing input .txt documents
OUT_DIR=data/outputs         # Directory for output reports

# Concurrency Configuration
MAX_CONCURRENCY=3            # Maximum number of documents to process in parallel

# User Configuration
USER_ID=local_user           # User ID for session management
```

### Google ADK Setup

This project requires Google ADK (Agent Development Kit) to be properly configured. Ensure you have:
- Valid Google Cloud credentials
- ADK package installed (`google-adk>=1.22.0`)
- Appropriate API access enabled

## Usage

### Basic Usage

1. Place your text documents (`.txt` files) in the `data/` directory (or your configured `DOCS_DIR`)

2. Run the main script:
```bash
python main.py
```

3. Find the generated reports in the output directory (default: `data/outputs/`)

### Programmatic Usage

```python
import asyncio
from pathlib import Path
from main import answer_document

async def process_document():
    doc_id = "my_document"
    document_text = Path("data/my_document.txt").read_text()
    out_folder = Path("data/outputs")
    
    report_path = await answer_document(
        doc_id=doc_id,
        document_text=document_text,
        out_folder=out_folder,
        model="gemini-2.5-flash"
    )
    print(f"Report saved to: {report_path}")

asyncio.run(process_document())
```

## How It Works

The system processes documents through the following pipeline:

1. **Document Loading**: Scans the input directory for `.txt` files
2. **Question Processing**: For each document, answers 8 predefined questions:
   - Definition of the practice
   - Benefits and importance
   - When to use
   - When not to use (justifications)
   - Method selection criteria
   - Implementation guidelines
   - Evaluation methods
   - Alternative approaches when not used

3. **AI Analysis**: Uses Google Gemini models via ADK to answer each question using only the document content
4. **Report Generation**: Combines all answers into a structured Markdown report with consistent formatting
5. **Output**: Saves each report as `{doc_id}_report.md` in the output directory

### Key Design Principles

- **Document-Only Responses**: The system is configured to use ONLY the provided document content—no external knowledge, common sense, or assumptions
- **Fail-Closed**: If information cannot be found in the document, the system outputs "Not found in document" rather than inventing content
- **Structured Output**: Reports follow a consistent structure with clear headings and subsections
- **Concurrent Processing**: Multiple documents are processed in parallel for efficiency

## Project Structure

```
Doc_QA/
├── main.py                 # Main entry point and orchestration
├── utils.py                # Utility functions for document loading and processing
├── my_agent/
│   ├── __init__.py
│   ├── agent.py            # Agent creation and session management
│   └── prompts.py          # System instructions and question definitions
├── data/                   # Input documents directory
│   └── outputs/            # Generated reports directory
├── pyproject.toml          # Project dependencies and metadata
├── .env                    # Environment variables (create this)
└── README.md               # This file
```

## Output Format

Each generated report follows this structure:

```markdown
# Best-practice guidance report

## Document: {doc_id}

## Q1: What is the definition of this practice?
[Answer with structured subsections]

## Q2: Why is this practice beneficial or important?
[Answer with structured subsections]

...

## Q8: If it is justified to not use this practice, then what should be done as an alternative?
[Answer with structured subsections]
```

Reports include relevant subsections such as:
- Key messages
- Definition and purpose
- Why this matters (benefits and importance)
- When to use
- When it may be justified not to use
- How to select appropriate methods
- How to implement
- How to evaluate
- Alternatives/mitigation steps

## Dependencies

- `google-adk>=1.22.0` - Google Agent Development Kit
- `dotenv>=0.9.9` - Environment variable management
- `tqdm>=4.67.1` - Progress bars
- `pre-commit>=4.5.1` - Git hooks for code quality

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Pouria Mortezaagha

---

**Note**: This system is designed to analyze documents and generate guidance reports. Ensure you have appropriate permissions and comply with data privacy regulations when processing documents.