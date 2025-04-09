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
    compatible format (hyphenated filename, no .md for pages, URL-encoded).
    Example: "Folder/Page Name" -> "Folder/Page-Name"
             "My Doc.pdf" -> "My-Doc.pdf"
             "#Header Name" -> "#header-name"
    """
    # Keep internal anchor links starting with #
    if target.startswith('#'):
        # Lowercase and hyphenate for anchor links
        return '#' + target[1:].replace(' ', '-').lower()
    else:
        # Handle page or file links (potentially with paths)
        parts = target.split('/')
        filename = parts[-1]
        path_components = parts[:-1]

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


        # Reconstruct the full path
        full_path_parts = path_components + [normalized_filename]
        final_target = "/".join(full_path_parts)

        # URL-encode the final path for safety (handles spaces in dirs if any, plus other chars)
        # Note: We already replaced spaces in the filename part.
        # GitHub typically expects hyphens for spaces in page names in the URL.
        return urllib.parse.quote(final_target)

def transform_obsidian_link(m, current_file_path=None): # Added current_file_path (optional for future use)
    """
    Transforms Obsidian links to GitHub standard Markdown links.
    [[Page Name]] -> [Page Name](Page-Name)
    [[Page Name|Link Text]] -> [Link Text](Page-Name)
    [[Folder/Page Name]] -> [Page Name](Folder/Page-Name)
    [[Folder/Page Name|Link Text]] -> [Link Text](Folder/Page-Name)
    [[#Header]] -> [Header](#header)
    [[#Header|Text]] -> [Text](#header)
    """
    prefix = m.group(1) # Keep leading non-exclamation mark char if present
    target = m.group(2).strip() # Raw target
    link_text = m.group(4).strip() if m.group(4) else target # Use target as text if no | alias

    normalized_target = normalize_link_target(target)

    # Use the last part of the target path as default link text if no alias is given
    if link_text == target and '/' in target:
        link_text = target.split('/')[-1]
        # If original target had .md, remove it from default text too
        if link_text.lower().endswith('.md'):
            link_text = link_text[:-3]
        # Also remove extension for assets in default text? Optional, can be verbose.
        # name_part, *ext_part = link_text.rsplit('.', 1)
        # if ext_part and re.search(r'\.(png|jpg|jpeg|gif|svg|pdf)$', link_text, re.IGNORECASE):
        #     link_text = name_part


    # Handle explicit header links within the same page [[#Header|Text]]
    # Note: normalize_link_target already handles the # correctly
    # This specific regex block might be redundant if the main one catches it,
    # but let's keep the structure for clarity.
    # The main regex already handles [[#Header|Text]] case via normalize_link_target

    sub = f"{prefix or ''}[{link_text}]({normalized_target})"
    print(f"  Transforming Link: {m.group(0)} -> {sub}")
    return sub


def transform_obsidian_embed(m):
    """
    Transforms Obsidian embeds to GitHub standard Markdown image/file links.
    ![[Image Name.png]] -> ![Image Name](Image-Name.png)
    ![[Folder/Doc Name.pdf]] -> ![Doc Name](Folder/Doc-Name.pdf) (Note: GitHub doesn't embed PDFs, this becomes a link)
    """
    target = m.group(1).strip()

    # Generate Alt Text: Use filename part, replace hyphens/underscores with spaces
    alt_text = Path(target).stem.replace('-', ' ').replace('_', ' ')

    # Normalize the target path similar to links (hyphenate filename part, URL encode)
    parts = target.split('/')
    filename = parts[-1]
    path_components = parts[:-1]

    name_part, *ext_part = filename.rsplit('.', 1)
    extension = ('.' + ext_part[0]) if ext_part else ''

    normalized_name = name_part.replace(' ', '-')
    normalized_filename = normalized_name + extension # Keep the extension!

    full_path_parts = path_components + [normalized_filename]
    final_target_path = "/".join(full_path_parts)
    encoded_target_path = urllib.parse.quote(final_target_path) # URL Encode the result

    # Decide if it's an image or just a file link based on extension
    is_image = re.search(r'\.(png|jpg|jpeg|gif|svg)$', target, re.IGNORECASE)

    if is_image:
        sub = f"![{alt_text}]({encoded_target_path})"
        print(f"  Transforming Image Embed: ![[{target}]] -> {sub}")
    else:
        # For non-images (like PDFs), use a standard link syntax
        sub = f"[{alt_text or filename}]({encoded_target_path})" # Use filename if alt_text is empty
        print(f"  Transforming File Embed: ![[{target}]] -> {sub}")

    return sub

# --- Main Processing Logic ---

def process_files(wiki_dir_path):
    """Finds Markdown files and applies transformations."""
    wiki_dir = Path(wiki_dir_path)
    if not wiki_dir.is_dir():
        print(f"Error: Wiki directory not found at '{wiki_dir_path}'")
        sys.exit(1)

    print(f"Processing Markdown files in: {wiki_dir}")
    # Use rglob to find md files recursively
    mdfiles = sorted(wiki_dir.rglob("*.md"))
    if not mdfiles:
        print("No Markdown files found to process.")
        return

    for file in mdfiles:
        if not file.is_file():
            continue
        relative_path = file.relative_to(wiki_dir)
        print(f"\nProcessing file: {relative_path}")
        try:
            original_text = file.read_text(encoding='utf-8')
            new_text = original_text

            # Apply transformations
            # 1. Standard Links: [[Link]] or [[Link|Text]] (ensure not preceded by !)
            #    Handles page links, file links, and links with paths.
            #    Pass the file's path in case future logic needs it (e.g., relative path calculation)
            new_text = re.sub(r"([^!])\[\[([^#\|\[\]]+)(\|([^#\|\[\]]+))?\]\]", lambda m: transform_obsidian_link(m, file), new_text)

            # 2. Header Links: [[#Header]] or [[#Header|Text]]
            #    Use a specific regex or ensure the main one handles it correctly via normalize_link_target.
            #    This regex ensures it ONLY matches #... links
            new_text = re.sub(r"\[\[(#[^\|\[\]]+)(\|([^\|\[\]]+))?\]\]", lambda m: transform_obsidian_link( ('', m.group(1), m.group(2), m.group(3)), file ), new_text) # Simulate groups for transform_obsidian_link

            # 3. Embeds: ![[File.ext]] or ![[Folder/File.ext]]
            new_text = re.sub(r"!\[\[([^\[\]]+)\]\]", transform_obsidian_embed, new_text)

            # Write back if changed
            if new_text != original_text:
                print(f"  Writing changes to {relative_path}")
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