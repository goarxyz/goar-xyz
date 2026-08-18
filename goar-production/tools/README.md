
Drop Python scripts here to auto-register them as agent tools.
Each script must export:

- `name: str`          — tool name (lowercase, no spaces)
- `description: str`   — what the tool does
- `parameters: dict`    — JSON Schema for arguments
- `run(**kwargs) -> str` — the implementation

The agent scans this folder once at startup. Use /reload to pick up new tools.
