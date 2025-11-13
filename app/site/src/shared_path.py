from pathlib import Path
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
STATIC_DIR = PUBLIC_DIR / "static"
TEMPLATES_DIR = PUBLIC_DIR / "templates"

templates = Jinja2Templates(directory=TEMPLATES_DIR)
