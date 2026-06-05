import os
from supabase import create_client, Client

# Esto le dice a Python: "Busca las etiquetas que guardamos en Render"
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(url, key)