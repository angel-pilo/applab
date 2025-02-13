import random
import string

def generar_password(longitud=12):
    caracteres = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(random.choice(caracteres) for _ in range(longitud))
