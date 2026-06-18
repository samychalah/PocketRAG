import os
import sys
import json
import shutil
from pathlib import Path

def install():
    print("🪶 Installing PocketRAG Skill & MCP Server...")
    
    # 1. Resolve absolute paths
    repo_dir = Path(__file__).resolve().parents[2]
    mcp_dir = repo_dir / "mcp"
    venv_python = mcp_dir / ".venv" / "bin" / "python3"
    config_yaml = mcp_dir / "config.yaml"
    
    print(f"Detected Repository Root: {repo_dir}")
    
    # 2. Install the Skill globally for Gemini/Antigravity
    gemini_config_dir = Path.home() / ".gemini" / "config"
    global_skill_dir = gemini_config_dir / "skills" / "pocketrag"
    
    print(f"Installing skill files to {global_skill_dir}...")
    try:
        global_skill_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_dir / "skills" / "pocketrag" / "SKILL.md", global_skill_dir / "SKILL.md")
        shutil.copy2(repo_dir / "skills" / "pocketrag" / "README.md", global_skill_dir / "README.md")
        print("✅ Skill files installed successfully!")
    except Exception as e:
        print(f"⚠️ Warning: Could not install skill files to {global_skill_dir}: {e}")
        print("You can still use the MCP server directly.")
        
    # 3. Configure Claude Desktop if present
    claude_config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if claude_config_path.exists() or claude_config_path.parent.exists():
        print(f"\nConfiguring Claude Desktop at {claude_config_path}...")
        try:
            claude_config_path.parent.mkdir(parents=True, exist_ok=True)
            config_data = {}
            if claude_config_path.exists():
                with open(claude_config_path, "r") as f:
                    try:
                        config_data = json.load(f)
                    except json.JSONDecodeError:
                        print("⚠️ Warning: claude_desktop_config.json is not valid JSON. Starting with clean config.")
            
            if "mcpServers" not in config_data:
                config_data["mcpServers"] = {}
                
            config_data["mcpServers"]["pocketrag"] = {
                "command": str(venv_python),
                "args": ["-m", "pocketrag.server"],
                "env": {
                    "NBLM_CONFIG": str(config_yaml)
                }
            }
            
            with open(claude_config_path, "w") as f:
                json.dump(config_data, f, indent=2)
            print("✅ Claude Desktop configuration updated successfully!")
        except Exception as e:
            print(f"❌ Failed to configure Claude Desktop: {e}")
    else:
        print("\nℹ️ Claude Desktop not detected. Skipping Claude configuration.")
        
    # 4. Print manual instructions for Cursor
    print("\n==========================================================")
    print("🎉 INSTALLATION COMPLETE!")
    print("==========================================================")
    print("To use PocketRAG in Cursor:")
    print("1. Open Cursor Settings > Features > MCP.")
    print("2. Click '+ Add New MCP Server'.")
    print("3. Enter the following details:")
    print("   - Name: pocketrag")
    print("   - Type: command")
    print(f"   - Command: {venv_python} -m pocketrag.server")
    print("==========================================================")

if __name__ == "__main__":
    install()
