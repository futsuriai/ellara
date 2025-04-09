#!/usr/bin/env python3
import sys
from pathlib import Path
import argparse
import urllib.parse # Keep for potential future use, though not encoding target now

# --- Configuration ---
# Files/dirs to exclude completely from navigation lists
EXCLUDE_ITEMS = {'.git', '_Sidebar.md', 'Home.md', '.obsidian', '.github', 'README.md'}

def generate_wiki_link(file_path: Path, wiki_root: Path):
    """Generates display text and link target for a wiki page file.
       TARGET CONTAINS FILENAME ONLY (hyphenated). Discards path.
       WARNING: This may break links if pages are not at the root.
    """
    stem = file_path.stem # Filename without extension e.g., "Page Name"
    # Make display text more readable (keep spaces here)
    display_text = stem.replace('-', ' ').replace('_', ' ')

    # --- MODIFICATION ---
    # Link target is ONLY the hyphenated stem (filename part), path discarded.
    link_target = stem.replace(' ', '-')
    # --- END MODIFICATION ---

    # No path components included based on user request.
    # No URL encoding applied here, assuming simple hyphenated names.

    return display_text, link_target

def generate_markdown_for_dir(directory_path: Path, wiki_root: Path, level: int):
    """Recursively generates markdown list items for a directory's contents."""
    markdown_lines = []
    indent = '  ' * level # Two spaces per indentation level
    # print(f"{indent}DEBUG: Processing directory: {directory_path}") # Optional debug

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
            # print(f"{indent}  DEBUG: Found directory: {item.name}") # Optional debug
            markdown_lines.append(f"{indent}* **{folder_name}**")
            markdown_lines.extend(generate_markdown_for_dir(item, wiki_root, level + 1))

        elif item.is_file() and item.suffix.lower() == '.md':
            # print(f"{indent}  DEBUG: Found MD file: {item.name}") # Optional debug
            try:
                display_text, link_target = generate_wiki_link(item, wiki_root) # Uses modified function
                # print(f"{indent}    DEBUG: Generated link parts: display='{display_text}', target='{link_target}'") # Optional debug
                markdown_line = f"{indent}* [{display_text}]({link_target})"
                # print(f"{indent}    DEBUG: Appending Markdown: {markdown_line}") # Optional debug
                markdown_lines.append(markdown_line)
            except Exception as e:
                print(f"{indent}    ERROR generating link for {item.name}: {e}")

    return markdown_lines

# --- Main execution block ---
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
                try:
                    # Try to derive a sensible repo name for the title
                    repo_name = wiki_dir.parent.name.split('.wiki')[0]
                except:
                    repo_name = "Wiki" # Fallback title
                home_title = f"# Welcome to the {repo_name.capitalize()} Wiki\n\n"
                f.write(home_title)
                f.write("Browse the wiki content using the sidebar or the structure below:\n\n")
                f.write("\n".join(all_markdown_lines))
                f.write("\n")
            print(f"Home page file '{args.home_file}' generated successfully.")
        except Exception as e:
            print(f"Error writing home page file {home_path}: {e}")

    print("\nNavigation generation script finished.")