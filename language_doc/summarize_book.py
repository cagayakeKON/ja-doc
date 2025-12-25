import os
import re
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Check for API key
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("Warning: OPENROUTER_API_KEY not found in environment variables.")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

MODEL = "google/gemini-2.5-flash-lite"

def summarize_chunk(text):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that summarizes Japanese textbook content."
            },
            {
                "role": "user",
                "content": f"Please summarize the following unit from a textbook. Extract key grammar points, vocabulary lists, and main topics. Output in Markdown.\n\n{text}"
            }
        ]
    )
    return response.choices[0].message.content

def split_into_units(text):
    # Regex for "第X课" or "第X課" (Lesson X)
    # Allows for some whitespace and digits
    pattern = re.compile(r'(第\s*\d+\s*[课課])')
    
    parts = pattern.split(text)
    
    units = []
    # parts[0] is usually intro before first lesson matches
    if parts[0].strip():
        units.append(("Intro", parts[0]))
        
    # After split, the captured group (the delimiter) is included in the list.
    # [content_before, delimiter, content_after, delimiter, content_after...]
    # Example: "Intro" "第1课" "Lesson 1 content..." "第2课" "Lesson 2 content..."
    
    # We iterate starting from index 1 (the first delimiter)
    for i in range(1, len(parts), 2):
        title = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ""
        
        # Combine title and content for context if needed, but usually we just want content
        # Actually, let's pass clear text
        units.append((title, content))
        
    return units

def main():
    parser = argparse.ArgumentParser(description="Summarize textbook markdown by unit.")
    parser.add_argument("md_path", help="Path to the full markdown file")
    parser.add_argument("--output_dir", default="summary_output", help="Directory to save summaries")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(args.md_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    print("Splitting content into units...")
    units = split_into_units(content)
    print(f"Found {len(units)} units.")
    
    full_summary = ""
    
    for title, text in units:
        print(f"Summarizing {title}...")
        # Clean title for filename
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip()
        
        try:
            summary = summarize_chunk(text)
            
            # Save individual summary
            unit_path = output_dir / f"{safe_title}.md"
            with open(unit_path, "w", encoding="utf-8") as f:
                f.write(f"# Summary: {title}\n\n{summary}")
            
            full_summary += f"\n\n# {title}\n\n{summary}"
            
        except Exception as e:
            print(f"Error summarizing {title}: {e}")

    # Save full summary
    full_path = output_dir / "full_summary.md"
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(full_summary)

    print(f"Done! Summaries saved to {output_dir}")

if __name__ == "__main__":
    main()
