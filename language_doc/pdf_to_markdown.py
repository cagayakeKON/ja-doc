import os
import base64
import argparse
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

# Check for API key
# Using the key provided by user if env var is missing
api_key = os.getenv("OPENROUTER_API_KEY") or "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"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

MODEL = "google/gemini-2.5-flash-lite"

def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def image_to_markdown(image, page_num):
    base64_image = encode_image(image)
    
    prompt_text = """
    Please convert this page of a Japanese textbook into Markdown with high fidelity.
    
    Rules:
    1. **Furigana (Ruby)**: If you see Kanji with furigana (reading above it), you MUST use HTML `<ruby>` tags.
       Example: `<ruby>私<rt>わたし</rt></ruby>`.
    2. **Structure**: Preserve hierarchy (Dialogs, Sentences, Headers). Use Markdown headers (#, ##).
    3. **Ignore Noise**: Do NOT include page headers or footers (especially page numbers).
    4. **Tables**: Convert tables to Markdown tables.
    5. **Images**: Describe images briefly in brackets like [Image: description].
    6. **Output**: Return ONLY the markdown content.
    """
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    )
    return response.choices[0].message.content

def main():
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown using Gemini 2.5 Flash Lite via OpenRouter.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output_dir", default="output", help="Directory to save markdown files")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Converting {args.pdf_path}...")
    
    try:
        doc = fitz.open(args.pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return
    
    # Initialize the full text file
    full_path = output_dir / "full_text.md"
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(f"<!-- Source: {args.pdf_path} -->\n\n")

    # Process pages
    total_pages = len(doc)
    print(f"Total pages: {total_pages}")
    
    for i, page in enumerate(doc):
        page_num = i + 1
        print(f"Processing page {page_num}/{total_pages}...")
        try:
            # Render page to image (pixmap)
            pix = page.get_pixmap(dpi=300) # Higher DPI for better furigana recognition
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            md_text = image_to_markdown(image, page_num)
            
            # Formatted page entry
            page_entry = f"\n<div id='page_{page_num}'>Page {page_num}</div>\n\n{md_text}\n---\n"
            
            # Append to full file immediately
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(page_entry)
                
            # Still save individual page for debugging/backup if needed (optional, keeping it for now)
            page_path = output_dir / f"page_{page_num:03d}.md"
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(md_text)
            
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
        
    print(f"Done! Saved to {output_dir}")

if __name__ == "__main__":
    main()
