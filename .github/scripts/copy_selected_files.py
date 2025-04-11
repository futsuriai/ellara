import sys
import shutil
from pathlib import Path
import os
import re

# Files to INCLUDE in publishing (ONLY these files will be copied)
FORCE_INCLUDE = {'Dusk of the Final Day - Light Between Worlds.md'}

# Files that should not be deleted when cleaning the target directory
PRESERVE_FILES = {'.git', 'CNAME'}

def add_front_matter(content, title):
    """Add Jekyll front matter to the content if it doesn't exist already."""
    # Check if front matter already exists
    if content.startswith('---'):
        return content
        
    front_matter = f"""---
layout: story
title: "{title}"
author: "The Writer"
---

"""
    return front_matter + content

def extract_title_from_content(content):
    """Extract title from the first heading in the content and remove it."""
    # Look for a Markdown heading at the beginning of the file
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        # Remove the title from the content
        content = content[:match.start()] + content[match.end():]
        return title, content.strip()
    return None, content

def copy_selected_files(source_dir, target_dir):
    source = Path(source_dir).resolve()
    target = Path(target_dir).resolve()
    
    # Get config directory path (sibling to scripts directory)
    config_dir = Path(__file__).parent.parent / "config"

    # Create target directory if it doesn't exist
    target.mkdir(parents=True, exist_ok=True)
    
    # Clean the target directory (remove all files except preserved ones)
    print("Cleaning target directory...")
    for item in target.glob('*'):
        if item.name not in PRESERVE_FILES:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    
    # Copy config files to target directory
    print("Copying configuration files...")
    
    # Create index file
    with open(target / "index.md", "w") as f:
        f.write("""---
layout: story
title: "404 Not Found"
---""")

    
    with open(target / "published.md", "w") as f:
        f.write("""---
layout: story
title: "Published Documents"
---
                
""")
    # Add links to all force-included files
        for filename in sorted(FORCE_INCLUDE):
            display_name = filename.replace('.md', '')
            web_friendly_name = filename.replace(' ', '-')
            link_name = web_friendly_name.replace('.md', '')
            f.write(f"- [{display_name}]({link_name})\n")

    # Copy _config.yml
    shutil.copy2(config_dir / "_config.yml", target / "_config.yml")
    
    # Create necessary directories for assets/css
    (target / "assets" / "css").mkdir(parents=True, exist_ok=True)
    
    # Copy style.scss
    shutil.copy2(config_dir / "assets" / "css" / "style.scss", 
                target / "assets" / "css" / "style.scss")
    
    # Copy _layouts directory and its contents (for story layout)
    if (config_dir / "_layouts").exists():
        layouts_dir = target / "_layouts"
        layouts_dir.mkdir(parents=True, exist_ok=True)
        for layout_file in (config_dir / "_layouts").glob("*"):
            shutil.copy2(layout_file, layouts_dir / layout_file.name)
            print(f"Copied layout: {layout_file.name}")
    
    # Copy _includes directory and its contents (for head include)
    if (config_dir / "_includes").exists():
        includes_dir = target / "_includes"
        includes_dir.mkdir(parents=True, exist_ok=True)
        for include_file in (config_dir / "_includes").glob("*"):
            shutil.copy2(include_file, includes_dir / include_file.name)
            print(f"Copied include: {include_file.name}")
    
    # Create necessary directories for assets/js
    if (config_dir / "assets" / "js").exists():
        js_dir = target / "assets" / "js"
        js_dir.mkdir(parents=True, exist_ok=True)
        # Copy dark-mode.js and any other JS files
        for js_file in (config_dir / "assets" / "js").glob("*"):
            shutil.copy2(js_file, js_dir / js_file.name)
            print(f"Copied JS file: {js_file.name}")

    # Find and copy only the specifically included files
    print("Copying selected files...")
    files_found = 0
    
    for item in source.rglob('*'):
        if item.is_file() and item.name in FORCE_INCLUDE:
            # Create a web-friendly version of the filename (replace spaces with hyphens)
            web_friendly_name = item.name.replace(' ', '-')
            # Read the content of the original file
            with open(item, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to extract the title from the content, or use the filename
            title, content = extract_title_from_content(content)
            if not title:
                title = item.name.replace('.md', '')
                
            # Add front matter to the content
            modified_content = add_front_matter(content, title)
            
            # Write the modified content to the destination
            dest_path = target / web_friendly_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
                
            files_found += 1
            print(f"Copied and added front matter to: {item.name} as {web_friendly_name}")
    
    print(f"Total files copied: {files_found}")
    if files_found < len(FORCE_INCLUDE):
        missing = set(FORCE_INCLUDE) - {item.name for item in source.rglob('*') if item.name in FORCE_INCLUDE}
        print(f"Warning: Could not find the following files: {missing}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python copy_selected_files.py <source_dir> <target_dir>")
        sys.exit(1)
        
    copy_selected_files(sys.argv[1], sys.argv[2])
    print(f"Files successfully copied to {sys.argv[2]}")