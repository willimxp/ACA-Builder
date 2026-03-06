# 260306 这个脚本已经没有用处了
# 因为已经将翻译资源整合到了en_US.po文件中
# 不再通过zh_HANS.py或en_US.py文件来管理字典

# 这个脚本用于更新zh_HANS.py文件中的翻译字符串
# 先手工修改zh_HANS.py文件中的翻译字符串，然后运行这个脚本
# 脚本会读取zh_HANS.py，然后根据git diff HEAD的结果，更新所有引用到对应索引的逻辑代码
# 运行方式，在终端中执行：
# python3 locale/i18n_update.py

import os
import sys
import re
import subprocess

def get_git_diff(project_root, file_rel_path):
    """
    Executes git diff HEAD to compare the current file (including staged/unstaged changes)
    with the HEAD version.
    """
    try:
        # Check if git exists
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, check=True)
    except (OSError, subprocess.CalledProcessError):
        print("Error: git is not installed or not in PATH.")
        sys.exit(1)

    # Run git diff -U0 HEAD -- <file>
    # -U0: 0 lines of context, useful for parsing contiguous changes
    cmd = ["git", "diff", "-U0", "HEAD", "--", file_rel_path]
    
    try:
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            print(f"Error running git diff: {result.stderr}")
            sys.exit(1)
        return result.stdout
    except Exception as e:
        print(f"Exception while running git: {e}")
        sys.exit(1)

def parse_diff_renames(diff_output):
    """
    Parses git diff output to find key renames in the translations dictionary.
    Returns a list of (old_key, new_key).
    """
    renames = []
    
    # Regex to match the dictionary lines in zh_HANS.py
    # Typical line: ("*", "Key"): "Value",
    # Regex breakdown:
    # ^\s*([-+])       : Start of line, optional whitespace, capture - or +
    # \s*\(\s*         : Opening parenthesis of tuple
    # ["\'](.*?)["\']  : Context string (e.g. "*"), captured
    # \s*,\s*          : Comma
    # ["\'](.*?)["\']  : MsgID string (The Key), captured
    # \s*\)\s*:\s*     : Closing paren, colon
    # ["\'](.*?)["\']  : Translation string (The Value), captured
    line_pattern = re.compile(r'^\s*([-+])\s*\(\s*["\'](.*?)["\']\s*,\s*["\'](.*?)["\']\s*\)\s*:\s*["\'](.*?)["\']')

    current_hunk_removed = [] # List of (key, translation)
    current_hunk_added = []   # List of (key, translation)
    
    lines = diff_output.splitlines()
    
    for line in lines:
        # Hunk header (e.g., @@ -10,1 +10,1 @@) resets the current block
        if line.startswith('@@'):
            renames.extend(match_renames(current_hunk_removed, current_hunk_added))
            current_hunk_removed = []
            current_hunk_added = []
            continue
            
        match = line_pattern.match(line)
        if match:
            change_type = match.group(1)
            # context = match.group(2) # We don't use context for matching for now, assuming mostly "*"
            key = match.group(3)
            translation = match.group(4)
            
            if change_type == '-':
                current_hunk_removed.append((key, translation))
            elif change_type == '+':
                current_hunk_added.append((key, translation))
    
    # Process the last hunk
    renames.extend(match_renames(current_hunk_removed, current_hunk_added))
    
    return renames

def match_renames(removed, added):
    """
    Matches removed keys with added keys to infer renames.
    Strategies:
    1. Exact translation match (High confidence).
    2. Single-pair replacement in a hunk (Medium confidence).
    """
    matched = []
    
    # Create copies to modify
    rem_pool = removed.copy()
    add_pool = added.copy()
    
    # Strategy 1: Match by exact translation
    # If the Chinese translation is identical, it's very likely a Key rename.
    for r_key, r_trans in list(rem_pool):
        for a_key, a_trans in list(add_pool):
            if r_trans == a_trans:
                matched.append((r_key, a_key))
                # Remove from pool to prevent double matching
                if (r_key, r_trans) in rem_pool: rem_pool.remove((r_key, r_trans))
                if (a_key, a_trans) in add_pool: add_pool.remove((a_key, a_trans))
                break
    
    # Strategy 2: If we have exactly 1 removed and 1 added remaining in this hunk,
    # we assume it's a rename even if the translation changed slightly.
    if len(rem_pool) == 1 and len(add_pool) == 1:
        matched.append((rem_pool[0][0], add_pool[0][0]))
    
    return matched

def main():
    # 1. Determine paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    zh_hans_rel = os.path.join("locale", "zh_HANS.py")
    zh_hans_abs = os.path.join(project_root, zh_hans_rel)
    
    print(f"Project Root: {project_root}")
    print(f"Scanning git diff for {zh_hans_rel}...")
    
    # 2. Get Git Diff
    diff_output = get_git_diff(project_root, zh_hans_rel)
    
    if not diff_output:
        print("No changes detected in zh_HANS.py vs HEAD.")
        print("Tip: Modify 'locale/zh_HANS.py' first, then run this script.")
        return

    # 3. Parse Renames
    renames = parse_diff_renames(diff_output)
    
    if not renames:
        print("Changes detected, but no clear key renames found.")
        print("Ensure you modified lines like: ('*', 'Old'): 'Val' -> ('*', 'New'): 'Val'")
        return
        
    print(f"\nDetected {len(renames)} rename(s):")
    for old, new in renames:
        print(f"  - '{old}' -> '{new}'")
        
    # 4. Apply Changes
    print("\nApplying changes to codebase...")
    count = 0
    updated_files = []
    
    for root, dirs, files in os.walk(project_root):
        # Skip common non-source directories
        if any(x in root for x in ["site-packages", ".git", "__pycache__", "locale"]):
             # We skip locale folder to avoid modifying zh_HANS.py again (it's the source of truth)
             # But wait, if we skip locale, we might miss other locale files if they existed. 
             # Currently only zh_HANS.py exists and we read diff from it.
             pass
            
        for file in files:
            # Skip hidden/system files (especially macOS resource forks like ._file)
            if file.startswith("._"):
                continue

            if file.endswith(".py") and file != "zh_HANS.py" and file != "i18n_update.py":
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    file_changed = False
                    
                    for old_str, new_str in renames:
                        # Replace double quoted strings
                        if f'"{old_str}"' in new_content:
                            new_content = new_content.replace(f'"{old_str}"', f'"{new_str}"')
                            file_changed = True
                            
                        # Replace single quoted strings
                        if f"'{old_str}'" in new_content:
                            new_content = new_content.replace(f"'{old_str}'", f"'{new_str}'")
                            file_changed = True
                            
                    if file_changed:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"  Updated: {file}")
                        count += 1
                        updated_files.append(file)
                        
                except Exception as e:
                    print(f"  Error processing {file}: {e}")

    if count == 0:
        print("\nNo files needed updating (Old keys not found in other files).")
    else:
        print(f"\nSuccess! Updated {count} files.")

if __name__ == "__main__":
    main()
