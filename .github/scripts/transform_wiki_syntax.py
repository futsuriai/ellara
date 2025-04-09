#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import argparse
import urllib.parse

# --- Transformation Functions (Adjusted for GitHub Wiki GFM) ---

def normalize_link_target(target):
    """
    Converts Obsidian link target to GitHub Wiki compatible format.
    TARGET CONTAINS FILENAME ONLY (hyphenated), discarding the path, EXCEPT for known asset types.
    No .md for pages. URL-encoded.
    WARNING: Discarding paths may break links if pages are not unique/at the root.
    Example: "Folder Name/Page Name" -> Page-Name
             "Folder Name/My Doc.pdf" -> Folder-Name/My-Doc.pdf (Assets keep path & get hyphenated dirs)
             "#Header Name" -> #header-name
    """
    if target.startswith('#'):
        # Anchor link: lowercase and hyphenate
        return '#' + target[1:].replace(' ', '-').lower()
    else:
        # Handle page or file links (potentially with paths)
        parts = target.split('/')
        filename = parts[-1] # Get the filename part

        # Check if filename looks like a known asset type that needs path preserved
        # NOTE: Adjust this regex if you have other non-markdown file types to link directly
        is_asset = re.search(r'\.(png|jpg|jpeg|gif|svg|pdf|zip|xlsx|docx|pptx)$', filename, re.IGNORECASE)

        if is_asset:
            # --- ASSET PATH LOGIC (Keep path, hyphenate dirs/name) ---
            path_components = [part.replace(' ', '-') for part in parts[:-1]] # Hyphenate dir parts
            name_part, *ext_part = filename.rsplit('.', 1)
            extension = ('.' + ext_part[0]) if ext_part else '' # Should always have extension here
            normalized_name = name_part.replace(' ', '-') # Hyphenate name part
            normalized_filename = normalized_name + extension
            full_path_parts = path_components + [normalized_filename]
            final_target = "/".join(full_path_parts)
            # --- END ASSET PATH LOGIC ---
        else:
            # --- PAGE LINK LOGIC (Discard path, use hyphenated filename only) ---
            name_part, *ext_part = filename.rsplit('.', 1)
            extension = ('.' + ext_part[0]) if ext_part else ''

            normalized_name = name_part.replace(' ', '-') # Hyphenate the name part

            # If it explicitly linked to .md, or had no extension, treat as wiki page (no ext)
            if extension.lower() == '.md' or not extension:
                final_target = normalized_name # DISCARD PATH, use hyphenated name only
            else:
                # Keep other extensions like .txt, but still discard path
                final_target = normalized_name + extension # DISCARD PATH
            # --- END PAGE LINK LOGIC ---

        # URL-encode the final path/target for safety
        return urllib.parse.quote(final_target)


def transform_obsidian_link(m, current_file_path=None): # Added current_file_path (optional for future use)
    """
    Transforms Obsidian links to GitHub standard Markdown links.
    [[Page Name]] -> [Page Name](Page-Name)
    [[Folder/Page Name|Link Text]] -> [Link Text](Page-Name) (Path discarded from target based on normalize_link_target)
    [[File.pdf]] -> [File.pdf](File.pdf)
    [[Folder/File.pdf]] -> [File.pdf](Folder/File.pdf) (Path kept for assets)
    [[#Header|Text]] -> [Text](#header)
    """
    prefix = m.group(1) # Keep leading non-exclamation mark char if present
    target = m.group(2).strip() # Raw target
    link_text_alias = m.group(4).strip() if m.group(4) else None # Explicit alias (like |Priory)

    normalized_target = normalize_link_target(target) # This now discards paths for non-assets

    # Determine the display text
    if link_text_alias:
        link_text = link_text_alias # Use the explicit alias if provided
    else:
        # No alias, use the filename part of the original target as default text
        link_text = target.split('/')[-1] # Get filename part from *original* target
        # Make default text more readable (remove .md, replace hyphens/underscores)
        if link_text.lower().endswith('.md'):
            link_text = link_text[:-3]
        link_text = link_text.replace('-', ' ').replace('_', ' ')


    sub = f"{prefix or ''}[{link_text}]({normalized_target})"
    # Optional Debug: Compare original target with new link
    # print(f"  Transforming Link: [[{target}{'|'+link_text_alias if link_text_alias else ''}]] -> {sub}")
    return sub


def transform_obsidian_embed(m):
    """
    Transforms Obsidian embeds to GitHub standard Markdown image/file links.
    KEEPS PATHS for embeds, hyphenates spaces in directory AND file paths.
    ![[Folder Name/Image Name.png]] -> ![Image Name](Folder-Name/Image-Name.png)
    """
    target = m.group(1).strip()
    # Alt text from filename part, made readable
    alt_text = Path(target).stem.replace('-', ' ').replace('_', ' ')

    parts = target.split('/')
    filename = parts[-1]
    # Hyphenate directory parts for the path
    path_components = [part.replace(' ', '-') for part in parts[:-1]]

    name_part, *ext_part = filename.rsplit('.', 1)
    extension = ('.' + ext_part[0]) if ext_part else ''

    # Hyphenate name part of filename
    normalized_name = name_part.replace(' ', '-')
    normalized_filename = normalized_name + extension # Keep the extension!

    # Reconstruct the full, hyphenated path
    full_path_parts = path_components + [normalized_filename]
    final_target_path = "/".join(full_path_parts)
    # URL Encode the result
    encoded_target_path = urllib.parse.quote(final_target_path)

    # Check if it's an image type for correct Markdown (image vs link)
    is_image = re.search(r'\.(png|jpg|jpeg|gif|svg)$', target, re.IGNORECASE)

    if is_image:
        sub = f"![{alt_text}]({encoded_target_path})"
        # print(f"  Transforming Image Embed: ![[{target}]] -> {sub}") # Optional Debug
    else:
        # For non-images (like PDFs), use a standard link syntax
        sub = f"[{alt_text or filename}]({encoded_target_path})" # Use filename if alt_text empty
        # print(f"  Transforming File Embed: ![[{target}]] -> {sub}") # Optional Debug

    return sub

# --- Main Processing Logic ---

def process_files(wiki_dir_path):
    """Finds Markdown files and applies transformations."""
    wiki_dir = Path(wiki_dir_path)
    if not wiki_dir.is_dir():
        print(f"Error: Wiki directory not found at '{wiki_dir_path}'")
        sys.exit(1)

    print(f"Processing Markdown files in: {wiki_dir}")
    mdfiles = sorted(wiki_dir.rglob("*.md"))
    if not mdfiles:
        print("No Markdown files found to process.")
        return

    for file in mdfiles:
        if not file.is_file() or file.name in ['_Sidebar.md', 'Home.md']: # Avoid processing nav files
            continue
        relative_path = file.relative_to(wiki_dir)
        # print(f"\nProcessing file: {relative_path}") # Optional Debug
        try:
            original_text = file.read_text(encoding='utf-8')
            new_text = original_text

            # Apply transformations using updated functions
            # 1. Standard Links: [[Link]] or [[Link|Text]] (ensure not preceded by !)
            new_text = re.sub(r"([^!])\[\[([^#\|\[\]]+)(\|([^#\|\[\]]+))?\]\]", lambda m: transform_obsidian_link(m, file), new_text)

            # 2. Header Links: [[#Header]] or [[#Header|Text]]
            new_text = re.sub(r"\[\[(#[^\|\[\]]+)(\|([^\|\[\]]+))?\]\]", lambda m: transform_obsidian_link( ('', m.group(1), m.group(2), m.group(3)), file ), new_text)

            # 3. Embeds: ![[File.ext]] or ![[Folder/File.ext]] (keeps paths)
            new_text = re.sub(r"!\[\[([^\[\]]+)\]\]", transform_obsidian_embed, new_text)

            # Write back if changed
            if new_text != original_text:
                print(f"  Writing changes to {relative_path}")
                file.write_text(new_text, encoding='utf-8')
            # else: # Optional Debug
                # print("  No changes needed.")
        except Exception as e:
            print(f"  Error processing file {file}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transform Obsidian Markdown for GitHub Wiki.")
    parser.add_argument("wiki_directory", help="Path to the checked-out wiki repository directory.")
    args = parser.parse_args()

    process_files(args.wiki_directory)
    print("\nWiki transformation script finished.")