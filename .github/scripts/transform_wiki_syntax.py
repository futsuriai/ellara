#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import argparse
import urllib.parse

# --- Transformation Functions (Adjusted for GitHub Wiki GFM) ---


def normalize_link_target(target):
    """
    Converts Obsidian link target (potentially with path) to GitHub Wiki
    compatible format (hyphenated filename AND directory names, no .md for pages, URL-encoded).
    Example: "Folder Name/Page Name" -> Folder-Name/Page-Name
             "My Doc.pdf" -> My-Doc.pdf
             "#Header Name" -> #header-name
    """
    if target.startswith('#'):
        # Anchor link: lowercase and hyphenate
        return '#' + target[1:].replace(' ', '-').lower()
    else:
        # Handle page or file links (potentially with paths)
        parts = target.split('/')
        filename = parts[-1]
        # --- MODIFICATION START ---
        # Hyphenate directory parts
        path_components = [part.replace(' ', '-') for part in parts[:-1]]
        # --- MODIFICATION END ---

        # Check if filename has a common asset extension (adjust list as needed)
        is_asset = re.search(r'\.(png|jpg|jpeg|gif|svg|pdf|zip|xlsx|docx|pptx)$', filename, re.IGNORECASE)

        # Split filename into name and extension (if it exists)
        name_part, *ext_part = filename.rsplit('.', 1)
        extension = ('.' + ext_part[0]) if ext_part else ''

        # Hyphenate the name part of the filename
        normalized_name = name_part.replace(' ', '-')

        # Reconstruct filename: keep extension for assets, omit .md for pages implicitly
        if is_asset:
            normalized_filename = normalized_name + extension
        elif extension.lower() == '.md':
             # If it explicitly links to "Page Name.md", treat as page link -> "Page-Name"
             normalized_filename = normalized_name
        else:
             # Assume it's a page link (no extension or non-asset extension)
             # DO NOT add .md suffix for GitHub Wiki page links
             normalized_filename = normalized_name + extension # Keep other extensions like .txt etc.


        # Reconstruct the full path using hyphenated components
        full_path_parts = path_components + [normalized_filename]
        final_target = "/".join(full_path_parts)

        # URL-encode the final path for safety (handles % chars etc.)
        # This should be safe even with hyphens already added.
        return urllib.parse.quote(final_target)


def transform_obsidian_embed(m):
    """
    Transforms Obsidian embeds to GitHub standard Markdown image/file links.
    Hyphenates spaces in directory AND file paths.
    ![[Folder Name/Image Name.png]] -> ![Image Name](Folder-Name/Image-Name.png)
    """
    target = m.group(1).strip()
    alt_text = Path(target).stem.replace('-', ' ').replace('_', ' ')

    parts = target.split('/')
    filename = parts[-1]
    # --- Ensure directory parts are hyphenated here too ---
    path_components = [part.replace(' ', '-') for part in parts[:-1]]

    name_part, *ext_part = filename.rsplit('.', 1)
    extension = ('.' + ext_part[0]) if ext_part else ''

    # Hyphenate name part of filename
    normalized_name = name_part.replace(' ', '-')
    normalized_filename = normalized_name + extension # Keep the extension!

    full_path_parts = path_components + [normalized_filename]
    final_target_path = "/".join(full_path_parts)
    encoded_target_path = urllib.parse.quote(final_target_path) # URL Encode the result

    is_image = re.search(r'\.(png|jpg|jpeg|gif|svg)$', target, re.IGNORECASE)

    if is_image:
        sub = f"![{alt_text}]({encoded_target_path})"
        print(f"  Transforming Image Embed: ![[{target}]] -> {sub}")
    else:
        sub = f"[{alt_text or filename}]({encoded_target_path})"
        print(f"  Transforming File Embed: ![[{target}]] -> {sub}")

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