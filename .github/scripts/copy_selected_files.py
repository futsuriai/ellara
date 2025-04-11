import sys
import shutil
from pathlib import Path
import os

# Files to INCLUDE in publishing (ONLY these files will be copied)
FORCE_INCLUDE = {'Dusk of the Final Day - Light Between Worlds.md'}

# Files that should not be deleted when cleaning the target directory
PRESERVE_FILES = {'.git', 'CNAME'}

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
    
    # Copy index.md
    # Create index file
    with open(target / "index.md", "w") as f:
        f.write("# Published Documentation\n\n")
        f.write("Welcome to the published documents.\n\n")
        f.write("## Available Documents\n\n")
        
        # Add links to all force-included files
        for filename in sorted(FORCE_INCLUDE):
            display_name = filename.replace('.md', '')
            web_friendly_name = filename.replace(' ', '-')
            link_name = web_friendly_name.replace('.md', '')
            f.write(f"- [{display_name}]({link_name})\n")


    # Copy _config.yml
    shutil.copy2(config_dir / "_config.yml", target / "_config.yml")
    
    # Create necessary directories for assets
    (target / "assets" / "css").mkdir(parents=True, exist_ok=True)
    
    # Copy custom.scss
    shutil.copy2(config_dir / "assets" / "css" / "style.scss", 
                target / "assets" / "css" / "style.scss")

    # Find and copy only the specifically included files
    print("Copying selected files...")
    files_found = 0
    
    for item in source.rglob('*'):
        if item.is_file() and item.name in FORCE_INCLUDE:
            # Create a web-friendly version of the filename (replace spaces with hyphens)
            web_friendly_name = item.name.replace(' ', '-')
            # Copy to root of target directory with the new name
            dest_path = target / web_friendly_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest_path)
            files_found += 1
            print(f"Copied: {item.name} as {web_friendly_name}")
    
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