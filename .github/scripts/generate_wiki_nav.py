#!/usr/bin/env python3
import sys
from pathlib import Path
import argparse
import urllib.parse # For potential future encoding needs

# --- Configuration ---
# Files/dirs to exclude completely from navigation lists
EXCLUDE_ITEMS = {'.git', '_Sidebar.md', 'Home.md', '.obsidian', '.github'} # Added .github

def generate_wiki_link(file_path: Path, wiki_root: Path):
    """Generates display text and link target for a wiki page file.
       Hyphenates spaces in BOTH directory and file names for the link target.
    """
    relative_path = file_path.relative_to(wiki_root)
    stem = file_path.stem # Filename without extension e.g., "Page Name"
    # Make display text more readable (keep spaces here)
    display_text = stem.replace('-', ' ').replace('_', ' ')

    # Create link target: Folder-With-Spaces/Sub-Folder/Page-Name
    link_parts = []
    # --- MODIFICATION START ---
    # Hyphenate EACH part of the path (directories)
    for part in relative_path.parent.parts:
        link_parts.append(part.replace(' ', '-')) # Hyphenate directory names
    # --- MODIFICATION END ---

    # Hyphenate the final file stem
    link_parts.append(stem.replace(' ', '-'))

    link_target = "/".join(link_parts)
    # Optional: URL encode potentially problematic characters?
    # Stick to hyphenation for now as it seems to be the key requirement.
    # link_target = urllib.parse.quote(link_target)
    return display_text, link_target

def generate_markdown_for_dir(directory_path: Path, wiki_root: Path, level: int):
    """Recursively generates markdown list items for a directory's contents."""
    markdown_lines = []
    indent = '  ' * level # Two spaces per indentation level
    # --- Debug Log ---
    print(f"{indent}DEBUG: Processing directory: {directory_path}")

    try:
        items_to_process = [
            item for item in directory_path.iterdir()
            if item.name not in EXCLUDE_ITEMS
        ]
        items = sorted(items_to_process, key=lambda x: x.name)
    except PermissionError:
        print(f"{indent}  WARNING: Permission denied reading directory {directory_path}. Skipping.")
        return []
    except Exception as e:
        print(f"{indent}  ERROR listing directory {directory_path}: {e}. Skipping.")
        return []

    for item in items:
        if item.name in EXCLUDE_ITEMS: # Redundant check, but safe
            continue

        if item.is_dir():
            folder_name = item.name.replace('-', ' ').replace('_', ' ')
             # --- Debug Log ---
            print(f"{indent}  DEBUG: Found directory: {item.name}")
            markdown_lines.append(f"{indent}* **{folder_name}**")
            markdown_lines.extend(generate_markdown_for_dir(item, wiki_root, level + 1))

        elif item.is_file() and item.suffix.lower() == '.md':
             # --- Debug Log ---
            print(f"{indent}  DEBUG: Found MD file: {item.name}")
            try:
                display_text, link_target = generate_wiki_link(item, wiki_root)
                 # --- Debug Log ---
                print(f"{indent}    DEBUG: Generated link parts: display='{display_text}', target='{link_target}'")
                markdown_line = f"{indent}* [{display_text}]({link_target})"
                 # --- Debug Log ---
                print(f"{indent}    DEBUG: Appending Markdown: {markdown_line}")
                markdown_lines.append(markdown_line)
            except Exception as e:
                 # --- Debug Log ---
                print(f"{indent}    ERROR generating link for {item.name}: {e}")
                # Optionally add a fallback placeholder if an error occurs:
                # display_text = item.stem.replace('-', ' ').replace('_', ' ')
                # markdown_lines.append(f"{indent}* {display_text} (Link generation error)")
        # else: # --- Debug Log --- Optional: Log ignored files
            # print(f"{indent}  DEBUG: Ignored item (not dir or md file): {item.name}")


    return markdown_lines

# --- Main execution block remains the same ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GitHub Wiki Sidebar/Home Markdown from directory structure.")
    parser.add_argument("wiki_directory", help="Path to the checked-out wiki repository directory.")
    parser.add_argument("--sidebar-file", default="_Sidebar.md", help="Output filename for the sidebar (relative to wiki_directory).")
    parser.add_argument("--home-file", default="Home.md", help="Output filename for the home page (relative to wiki_directory).")
    parser.add_argument("--no-home", action="store_true", help="Do not generate or overwrite the Home.md file.")
    parser.add_argument("--no-sidebar", action="store_true", help="Do not generate or overwrite the _Sidebar.md file.")

    args = parser.parse_args()

    wiki_dir = Path(args.wiki_directory).resolve()
    if not wiki_dir.is_dir():
        print(f"Error: Wiki directory not found at '{args.wiki_directory}' (resolved to '{wiki_dir}')")
        sys.exit(1)

    print(f"Generating navigation Markdown for directory: {wiki_dir}")
    all_markdown_lines = generate_markdown_for_dir(wiki_dir, wiki_dir, level=0)

    # --- Generate Sidebar ---
    if not args.no_sidebar:
        sidebar_path = wiki_dir / args.sidebar_file
        print(f"Writing sidebar structure to: {sidebar_path}")
        try:
            with open(sidebar_path, 'w', encoding='utf-8') as f:
                f.write("# Wiki Navigation\n\n")
                if not args.no_home:
                     home_page_stem = Path(args.home_file).stem
                     home_link_target = home_page_stem.replace(' ', '-')
                     f.write(f"* [{home_page_stem}]({home_link_target})\n")
                f.write("\n".join(all_markdown_lines))
                f.write("\n")
            print(f"Sidebar file '{args.sidebar_file}' generated successfully.")
        except Exception as e:
            print(f"Error writing sidebar file {sidebar_path}: {e}")

    # --- Generate Home Page (Optional) ---
    if not args.no_home:
        home_path = wiki_dir / args.home_file
        print(f"Writing home page structure to: {home_path}")
        try:
            with open(home_path, 'w', encoding='utf-8') as f:
                repo_name = wiki_dir.parent.name
                home_title = f"# Welcome to the {repo_name.split('.')[0].capitalize()} Wiki\n\n"
                f.write(home_title)
                f.write("Browse the wiki content using the sidebar or the structure below:\n\n")
                f.write("\n".join(all_markdown_lines))
                f.write("\n")
            print(f"Home page file '{args.home_file}' generated successfully.")
        except Exception as e:
            print(f"Error writing home page file {home_path}: {e}")

    print("\nNavigation generation script finished.")