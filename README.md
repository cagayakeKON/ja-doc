# AutoNote: PDF to Summary Tool

This project contains tools to convert a Japanese textbook PDF into Markdown and then summarize it unit by unit.

## Prerequisites

1.  **Python**: Ensure Python is installed.
2.  **uv**: This project uses `uv` for package management.
3.  **Poppler**: Required for processing PDFs.
    -   **Windows**: Download from [github.com/oschwartz10612/poppler-windows/releases](https://github.com/oschwartz10612/poppler-windows/releases), extract it, and add the `bin` folder to your System PATH.

## Setup

1.  **Install Dependencies**:
    ```powershell
    uv sync
    ```

2.  **Environment Variables**:
    -   Copy `.env.example` to `.env`.
    -   Add your OpenRouter API key:
        ```
        OPENROUTER_API_KEY=sk-or-v1-...
        ```

## Usage

### Step 1: Convert PDF to Markdown
Split the PDF into images and convert each page to Markdown using Gemini.

```powershell
uv run pdf_to_markdown.py "path/to/your/textbook.pdf" --output_dir "output_markdown"
```

### Step 2: Summarize Content
Read the generated Markdown, split it by units (e.g., "第1课"), and generate summaries.

```powershell
uv run summarize_book.py "output_markdown/full_text.md" --output_dir "output_summary"
```

## Configuration

-   **Model**: Default is `google/gemini-2.5-flash-lite`. You can change this in the scripts if needed.
