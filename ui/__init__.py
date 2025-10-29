"""ui - Interfaccia client JARVIS"""

from pathlib import Path

UI_DIR = Path(__file__).parent
INDEX_HTML_PATH = UI_DIR / "index.html"

__all__ = ["UI_DIR", "INDEX_HTML_PATH"]
