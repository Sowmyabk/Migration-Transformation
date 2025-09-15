import json
import re
import os
from pathlib import Path

# Define input and output directories
input_folder = r"D:/Polarion/Migration/Transformation/IBM JSON"
output_folder = r"D:/Polarion/Migration/Transformation/POLARION JSON"

# Create output folder if it doesn't exist
Path(output_folder).mkdir(parents=True, exist_ok=True)

# Function to clean up HTML content
def clean_html(html_text: str) -> str:
    if not html_text:
        return ""

    cleaned = html_text

    # Remove <ns0:primarytext ...> wrapper
    cleaned = re.sub(r"</?ns0:primarytext[^>]*>", "", cleaned)

    # Remove "html:" prefixes
    cleaned = re.sub(r"</?html:", "<", cleaned)

    # Remove dir and id attributes
    cleaned = re.sub(r'\s*dir="[^"]*"', "", cleaned)
    cleaned = re.sub(r'\s*id="[^"]*"', "", cleaned)

    # Remove <img> tags
    cleaned = re.sub(r"<img[^>]*>", "", cleaned)

    # Remove newlines and collapse spaces
    cleaned = re.sub(r"\n+", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)

    # Remove empty <p> and <div> (with or without &nbsp;)
    cleaned = re.sub(r"<p>\s*(?:&nbsp;)?\s*</p>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<div>\s*(?:&nbsp;)?\s*</div>", "", cleaned, flags=re.IGNORECASE)

    # Collapse duplicate <p> or <div> chains
    cleaned = re.sub(r"(</p>\s*<p>\s*)+", "</p><p>", cleaned)
    cleaned = re.sub(r"(</div>\s*<div>\s*)+", "</div><div>", cleaned)

    # Fix duplicated inline tags (<i><i>, <u><u>, etc.)
    cleaned = re.sub(r"<(i|u|b|sub|sup)><\1>", r"<\1>", cleaned)
    cleaned = re.sub(r"</(i|u|b|sub|sup)></\1>", r"</\1>", cleaned)

    # Remove stray closing tags at the end
    cleaned = re.sub(r"</(i|u|b|sub|sup|del)>\s*</", "</", cleaned)

    return cleaned.strip()

# Function to process a single JSON file
def process_json_file(file_path, output_path):
    try:
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check if the JSON has an 'artifacts' array
        if isinstance(data.get('artifacts'), list):
            for artifact in data['artifacts']:
                # Clean primary_text_html and primary_text_html_local if they exist
                if 'primary_text_html' in artifact:
                    artifact['primary_text_html'] = clean_html(artifact['primary_text_html'])
                if 'primary_text_html_local' in artifact:
                    artifact['primary_text_html_local'] = clean_html(artifact['primary_text_html_local'])
        else:
            # If no artifacts array, process the top-level fields directly
            if 'primary_text_html' in data:
                data['primary_text_html'] = clean_html(data['primary_text_html'])
            if 'primary_text_html_local' in data:
                data['primary_text_html_local'] = clean_html(data['primary_text_html_local'])

        # Save the cleaned JSON to the output folder
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"Processed: {file_path} -> {output_path}")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {file_path}: {e}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

# Iterate through all JSON files in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith('.json'):
        input_file_path = os.path.join(input_folder, filename)
        output_file_path = os.path.join(output_folder, filename)
        process_json_file(input_file_path, output_file_path)

print("All JSON files processed.")
