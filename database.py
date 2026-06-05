import os
from supabase import create_client, Client

# Leeremos las credenciales directamente del servidor en internet
url: str = os.environ.get("https://svfgjmudruxjijkimwdj.supabase.co")
key: str = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN2ZmdqbXVkcnV4amlqa2ltd2RqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA2MjY1MzksImV4cCI6MjA5NjIwMjUzOX0.MxWcYEOmF0k3dv5Cv0G91_pYebbRq7A-dAmRUR3_lP0")

supabase: Client = create_client(url, key)