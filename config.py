import os
from dotenv import load_dotenv

load_dotenv()  # Cargar las variables del archivo .env

class Config:
    # Configuración de Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY")  
