# supabase_client.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def normalize_supabase_url(value: str | None) -> str:
    """Return the project root URL expected by supabase-py."""
    url = (value or "").strip().rstrip("/")
    for suffix in ("/rest/v1", "/rest"):
        if url.endswith(suffix):
            url = url.removesuffix(suffix)
            break
    return url


SUPABASE_URL = normalize_supabase_url(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan SUPABASE_URL y/o SUPABASE_KEY en el archivo .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
