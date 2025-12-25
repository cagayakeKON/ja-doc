import os
import re
import json
import argparse
import uuid
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# API Key
api_key = os.getenv("OPENROUTER_API_KEY") or "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"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

MODEL = "google/gemini-3-flash-preview"

def preprocess_markdown(content):
    """
    Parse the markdown content and assign lesson numbers to each page.
    Rules:
    - Page 19 is the start of Lesson 1 (第1课)
    - When "第X课" is first encountered on a page, that page and subsequent pages are part of Lesson X
    - Returns a dict: { lesson_number: [page_contents...] }
    """
    # Split by page divs
    page_pattern = re.compile(r"<div id='page_(\d+)'>Page \d+</div>")
    
    parts = page_pattern.split(content)
    # parts will be: [before_first_page, page_num, content, page_num, content, ...]
    
    pages = {}
    for i in range(1, len(parts), 2):
        page_num = int(parts[i])
        page_content = parts[i+1] if i+1 < len(parts) else ""
        pages[page_num] = page_content
    
    # Assign lessons to pages
    lessons = {}
    current_lesson = 0
    lesson_pattern = re.compile(r'第\s*(\d+)\s*[课課]')
    
    for page_num in sorted(pages.keys()):
        page_content = pages[page_num]
        
        # Check for lesson start on this page
        match = lesson_pattern.search(page_content)
        if match:
            found_lesson = int(match.group(1))
            if found_lesson > current_lesson:
                current_lesson = found_lesson
        
        # Pages before 19 are intro/front matter
        if page_num < 19:
            if 0 not in lessons:
                lessons[0] = []
            lessons[0].append((page_num, page_content))
        else:
            # Page 19+ belongs to current lesson (at least lesson 1)
            if current_lesson == 0:
                current_lesson = 1  # Page 19 starts Lesson 1
            
            if current_lesson not in lessons:
                lessons[current_lesson] = []
            lessons[current_lesson].append((page_num, page_content))
    
    return lessons

def extract_grammar_from_lesson(lesson_num, lesson_pages):
    """
    Send lesson content to AI and get structured grammar points as JSON.
    """
    combined_text = "\n".join([f"--- Page {p} ---\n{c}" for p, c in lesson_pages])
    
    prompt = f"""
You are analyzing Lesson {lesson_num} (第{lesson_num}课) from a Japanese textbook.

Extract all grammar points. A single grammar header (like "〜ことができる") may have multiple sub-usages (e.g., Verb+ことができる, Noun+ができる).

For each Grammar Point, provide:
- lesson: "第{lesson_num}课"
- grammar_point: The main grammar header (e.g., "〜ことができる")
- importance: Score 1-10
- usages: A list of usage objects. Each usage object contains:
    - meaning: Specific meaning for this usage
    - structure: Form/Connection (e.g., "动词连体形+ことができる")
    - explanation: Brief explanation from text
    - example: A SINGLE example sentence object with "sentence" (Japanese+Ruby) and "translation" (Chinese).

Return ONLY a valid JSON array.

Example structure:
[
  {{
    "lesson": "第1课",
    "grammar_point": "〜ことができる",
    "importance": 10,
    "usages": [
      {{
        "meaning": "表示动作的可能性",
        "structure": "动词连体形 + ことができる",
        "explanation": "表示外部条件允许或本身有能力...",
        "example": {{
          "sentence": "<ruby>私<rt>わたし</rt></ruby>は<ruby>新聞<rt>しんぶん</rt></ruby>を<ruby>読<rt>よ</rt></ruby>むことができます。",
          "translation": "我能读报纸。"
        }}
      }},
      {{
        "meaning": "表示会某事",
        "structure": "体言 + ができる",
        "explanation": "表示掌握某种技能...",
        "example": {{
          "sentence": "あなたは<ruby>日本語<rt>にほんご</rt></ruby>ができますか。",
          "translation": "你会日语吗？"
        }}
      }}
    ]
  }}
]

Lesson content:
{combined_text}
"""
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = response.choices[0].message.content
            
            # Try to parse JSON from response
            # Sometimes AI wraps in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1)
            
            grammar_list = json.loads(response_text)
            return grammar_list
            
        except json.JSONDecodeError as e:
            print(f"  Warning: JSON Parse Error (Attempt {attempt+1}/{max_retries}): {e}")
        except Exception as e:
            print(f"  Warning: API/Other Error (Attempt {attempt+1}/{max_retries}): {e}")
    
    print(f"  Error: Failed to extract grammar for Lesson {lesson_num} after {max_retries} attempts.")
    return []

def main():
    parser = argparse.ArgumentParser(description="Extract grammar from preprocessed markdown by lesson.")
    parser.add_argument("md_path", help="Path to full_text.md")
    parser.add_argument("--output", default="grammar_data.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    print(f"Reading {args.md_path}...")
    with open(args.md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print("Preprocessing: Assigning lessons to pages...")
    lessons = preprocess_markdown(content)
    
    print(f"Found {len(lessons)} lesson groups (including intro if any).")
    for lesson_num in sorted(lessons.keys()):
        page_nums = [p for p, _ in lessons[lesson_num]]
        print(f"  Lesson {lesson_num}: Pages {min(page_nums)}-{max(page_nums)}")
    
    all_grammar = []
    
    # Skip lesson 0 (intro pages)
    for lesson_num in sorted(lessons.keys()):
        if lesson_num == 0:
            print(f"Skipping intro pages (Lesson 0)...")
            continue
        
        print(f"Extracting grammar from Lesson {lesson_num}...")
        lesson_pages = lessons[lesson_num]
        grammar_points = extract_grammar_from_lesson(lesson_num, lesson_pages)
        print(f"  Found {len(grammar_points)} grammar points.")
        all_grammar.extend(grammar_points)
    
    # Generate UUIDs for all grammar points after collection
    print("Generating UUIDs...")
    for item in all_grammar:
        item['id'] = str(uuid.uuid4())
    
    # Save to JSON
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_grammar, f, ensure_ascii=False, indent=2)
    
    print(f"Done! Saved {len(all_grammar)} grammar points to {output_path}")

if __name__ == "__main__":
    main()
