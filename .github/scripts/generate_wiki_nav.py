#!/usr/bin/env python3
import sys
from pathlib import Path
import argparse
import urllib.parse # For potential future encoding needs

# --- Configuration ---
# Files/dirs to exclude completely from navigation lists
EXCLUDE_ITEMS = {'.git', '_Sidebar.md', 'Home.md', '.obsidian'}
# Files that shouldn't be linked but might contain links (used by some wikis)
# Not strictly needed for GitHub Wiki sidebar/home generation typically.
# IGNORE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.pdf'}

def generate_wiki_link(file_path: Path, wiki_root: Path):
    """Generates display text and link target for a wiki page file."""
    relative_path = file_path.relative_to(wiki_root)
    stem = file_path.stem # Filename without extension e.g., "Page Name"
    # Make display text more readable
    display_text = stem.replace('-', ' ').replace('_', ' ')

    # Create link target: Folder/SubFolder/Page-Name (hyphenate page name part)
    link_parts = []
    # Keep original directory names. GitHub Wiki handles spaces/case ok here usually.
    # If needed, directory parts can also be normalized/encoded.
    for part in relative_path.parent.parts:
        link_parts.append(part)

    # Hyphenate the file stem for the link target (GitHub standard)
    link_parts.append(stem.replace(' ', '-'))

    link_target = "/".join(link_parts)
    # Basic URL encoding might be needed if names contain special chars,
    # but GitHub handles simple Folder/Page-Name well. Stick without for now.
    # link_target = urllib.parse.quote(link_target)
    return display_text, link_target

def generate_markdown_for_dir(directory_path: Path, wiki_root: Path, level: int):
    """Recursively generates markdown list items for a directory's contents."""
    markdown_lines = []
    indent = '  ' * level # Two spaces per indentation level

    # Sort items alphabetically for consistent order
    try:
        # Filter items *before* sorting to avoid errors on restricted files (.git)
        items_to_process = [
            item for item in directory_path.iterdir()
            if item.name not in EXCLUDE_ITEMS
        ]
        items = sorted(items_to_process, key=lambda x: x.name)
    except PermissionError:
        print(f"  Warning: Permission denied reading directory {directory_path}. Skipping.")
        return [] # Skip this directory
    except Exception as e:
        print(f"  Error listing directory {directory_path}: {e}. Skipping.")
        return []


    for item in items:
        # Double-check exclusion just in case iterdir listed it somehow
        if item.name in EXCLUDE_ITEMS:
            continue

        if item.is_dir():
            # Add folder entry - bold, not usually linked itself in sidebar
            folder_name = item.name.replace('-', ' ').replace('_', ' ')
            markdown_lines.append(f"{indent}* **{folder_name}**")
            # Recurse into subdirectory
            markdown_lines.extend(generate_markdown_for_dir(item, wiki_root, level + 1))
        elif item.is_file() and item.suffix.lower() == '.md':
            # Add file entry with link
            try:
                display_text, link_target = generate_wiki_link(item, wiki_root)
                markdown_lines.append(f"{indent}* [{display_text}]({link_target})")
            except Exception as e:
                 print(f"  Error generating link for {item}: {e}")
        # Optionally, add logic here to list other file types if desired

    return markdown_lines

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GitHub Wiki Sidebar/Home Markdown from directory structure.")
    parser.add_argument("wiki_directory", help="Path to the checked-out wiki repository directory.")
    parser.add_argument("--sidebar-file", default="_Sidebar.md", help="Output filename for the sidebar (relative to wiki_directory).")
    parser.add_argument("--home-file", default="Home.md", help="Output filename for the home page (relative to wiki_directory).")
    parser.add_argument("--no-home", action="store_true", help="Do not generate or overwrite the Home.md file.")
    parser.add_argument("--no-sidebar", action="store_true", help="Do not generate or overwrite the _Sidebar.md file.")

    args = parser.parse_args()

    wiki_dir = Path(args.wiki_directory).resolve() # Use absolute path
    if not wiki_dir.is_dir():
        print(f"Error: Wiki directory not found at '{args.wiki_directory}' (resolved to '{wiki_dir}')")
        sys.exit(1)

    print(f"Generating navigation Markdown for directory: {wiki_dir}")
    # Start recursion from the wiki root directory
    all_markdown_lines = generate_markdown_for_dir(wiki_dir, wiki_dir, level=0)

    # --- Generate Sidebar ---
    if not args.no_sidebar:
        sidebar_path = wiki_dir / args.sidebar_file
        print(f"Writing sidebar structure to: {sidebar_path}")
        try:
            with open(sidebar_path, 'w', encoding='utf-8') as f:
                # You can customize the sidebar header
                f.write("# Wiki Navigation\n\n")
                # Optionally add a link back to the Home page if you generate one
                if not args.no_home:
                     home_page_stem = Path(args.home_file).stem
                     home_link_target = home_page_stem.replace(' ', '-')
                     f.write(f"* [{home_page_stem}]({home_link_target})\n") # Link to Home

                f.write("\n".join(all_markdown_lines))
                f.write("\n") # Add trailing newline
            print(f"Sidebar file '{args.sidebar_file}' generated successfully.")
        except Exception as e:
            print(f"Error writing sidebar file {sidebar_path}: {e}")

    # --- Generate Home Page (Optional) ---
    if not args.no_home:
        home_path = wiki_dir / args.home_file
        print(f"Writing home page structure to: {home_path}")
        try:
            with open(home_path, 'w', encoding='utf-8') as f:
                 # Customize the home page title and intro
                repo_name = wiki_dir.parent.name # Try to get repo name from parent dir
                home_title = f"# Welcome to the {repo_name.split('.')[0].capitalize()} Wiki\n\n" # Remove .wiki suffix if present
                f.write(home_title)
                f.write("Browse the wiki content using the sidebar or the structure below:\n\n")
                f.write("\n".join(all_markdown_lines))
                f.write("\n") # Add trailing newline
            print(f"Home page file '{args.home_file}' generated successfully.")
        except Exception as e:
            print(f"Error writing home page file {home_path}: {e}")

    print("\nNavigation generation script finished.")