#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import argparse
import urllib.parse

# --- Transformation Functions (Adjusted for GitHub Wiki GFM) ---

def normalize_link_target(target):
    """Converts Obsidian link target to GitHub Wiki compatible format."""
    # Replace spaces with hyphens (common GitHub behavior for wiki page names)
    # Keep internal anchor links starting with #
    if target.startswith('#'):
        # Lowercase and hyphenate for anchor links
        return '#' + target[1:].replace(' ', '-').lower()
    else:
        # Hyphenate for page links, URL-encode special chars if needed, add .md
        # Basic hyphenation:
        page_name = target.replace(' ', '-')
        # Add .md suffix if it's not an external link or anchor
        if not page_name.startswith('#') and not re.match(r'^[a-zA-Z]+://', page_name):
             # Check if it already has a common file extension
            if not re.search(r'\.(md|png|jpg|jpeg|gif|pdf)$', page_name, re.IGNORECASE):
                page_name += '.md'
        return page_name

def transform_obsidian_link(m):
    """[[Page Name]] or [[Page Name|Link Text]] -> [Link Text](Page-Name.md)"""
    prefix = m.group(1) # Keep leading non-exclamation mark char
    target = m.group(2)
    link_text = m.group(4) if m.group(4) else target # Use target as text if no | alias

    # Handle internal page header links: [[#Header|Text]] -> [Text](#header)
    if target.startswith('#'):
        normalized_target = normalize_link_target(target)
        sub = f"{prefix}[{link_text}]({normalized_target})"
        print(f"  Transforming Header Link: {m.group(0)} -> {sub}")
        return sub
    # Handle page links: [[Page|Text]] -> [Text](Page.md) or [[Page]] -> [Page](Page.md)
    else:
        normalized_target = normalize_link_target(target)
        sub = f"{prefix}[{link_text}]({normalized_target})"
        print(f"  Transforming Page Link: {m.group(0)} -> {sub}")
        return sub

def transform_obsidian_embed(m):
    """![[Image.png]] -> ![Image.png](Image.png)"""
    target = m.group(1)
    # Assume image is in the same directory or copied to the root
    # More complex path logic might be needed depending on vault structure
    image_filename = target.split('/')[-1] # Get filename if path is included
    normalized_target = urllib.parse.quote(image_filename.replace(' ', '-')) # URL encode filename
    alt_text = Path(image_filename).stem # Use filename without extension as alt text
    sub = f"![{alt_text}]({normalized_target})"
    print(f"  Transforming Embed: ![[{target}]] -> {sub}")
    return sub

# --- Main Processing Logic ---

def process_files(wiki_dir_path):
    """Finds Markdown files and applies transformations."""
    wiki_dir = Path(wiki_dir_path)
    if not wiki_dir.is_dir():
        print(f"Error: Wiki directory not found at '{wiki_dir_path}'")
        sys.exit(1)

    print(f"Processing Markdown files in: {wiki_dir}")
    mdfiles = sorted(wiki_dir.glob("**/*.md"))

    for file in mdfiles:
        if not file.is_file():
            continue
        print(f"\nProcessing file: {file.relative_to(wiki_dir)}")
        try:
            original_text = file.read_text(encoding='utf-8')
            new_text = original_text

            # Apply transformations
            # Regex looks for [[link]] or [[link|text]], ensuring it's not preceded by ! (which denotes an embed)
            new_text = re.sub(r"([^!])\[\[([^#|\[\]]+)(\|([^#|\[\]]+))?\]\]", transform_obsidian_link, new_text)
             # Regex for header links: [[#Header|Text]]
            new_text = re.sub(r"\[\[(#[^#|\[\]]+)\|([^#|\[\]]+)\]\]", lambda m: transform_obsidian_link( ('', m.group(1), '|', m.group(2)) ), new_text) # Simulate groups for transform_obsidian_link
             # Regex for embeds: ![[File.ext]]
            new_text = re.sub(r"!\[\[([^\[\]]+)\]\]", transform_obsidian_embed, new_text)

            # Write back if changed
            if new_text != original_text:
                print(f"  Writing changes to {file.relative_to(wiki_dir)}")
                file.write_text(new_text, encoding='utf-8')
            else:
                print("  No changes needed.")
        except Exception as e:
            print(f"  Error processing file {file}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transform Obsidian Markdown for GitHub Wiki.")
    parser.add_argument("wiki_directory", help="Path to the checked-out wiki repository directory.")
    args = parser.parse_args()

    process_files(args.wiki_directory)
    print("\nWiki transformation script finished.")