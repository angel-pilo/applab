import os
from werkzeug.security import generate_password_hash
from supabase import create_client
from dotenv import load_dotenv

# Cargar las variables de entorno
load_dotenv()

# Obtener URL y clave de Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Crear el cliente de Supabase
supabase = create_client(supabase_url, supabase_key)

def add_user_and_employee(first_name, last_name, birthdate, email, phone, password, contacto_emergencia, alergias, role_id, gender, photo_url):
    # Generar username automático
    birth_year = birthdate.split("-")[0]  # Extraer año de nacimiento
    username = f"{first_name[0].lower()}{last_name.lower()}{birth_year}"

    # Encriptar la contraseña
    hashed_password = generate_password_hash(password)

    # Insertar usuario en la tabla "usuarios"
    user_data = {
        "username": username,
        "password": hashed_password,
        "email": email
    }
    user_response = supabase.table("usuarios").insert(user_data).execute()

    if user_response.data is None:
        return None, "Error al guardar el usuario."

    # Obtener el ID del usuario recién creado
    user_id = user_response.data[0]["id"]

    # Insertar empleado en la tabla "empleados"
    employee_data = {
        "first_name": first_name,
        "last_name": last_name,
        "birthdate": birthdate,
        "phone": phone,
        "user_id": user_id,  # Relación con la tabla usuarios
        "sexo": gender,  # Guardamos el sexo
        "contacto_emergencia": contacto_emergencia,
        "alergias": alergias,
        "foto_perfil": photo_url  # Guardamos la URL de la foto de perfil
    }
    employee_response = supabase.table("empleados").insert(employee_data).execute()

    if employee_response.data is None:
        return None, "Error al guardar el empleado."

    # Asignar el rol al empleado
    empleado_id = employee_response.data[0]["id"]
    role_data = {
        "empleado_id": empleado_id,
        "rol_id": role_id
    }
    role_response = supabase.table("empleado_roles").insert(role_data).execute()

    if role_response.data is None:
        return None, "Error al asignar el rol."

    return employee_response.data, "Empleado añadido correctamente"
