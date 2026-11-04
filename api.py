import hashlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector

app = FastAPI(title="EcoRuta API")

DB_CONFIG = {
    'host': 'ecoruta-antonio-618d.c.aivencloud.com',
    'port': 21716,
    'user': 'avnadmin',
    'password': 'AVNS_Yum4uq8V_ok00akE24o',
    'database': 'defaultdb'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def cifrar_contrasena(contrasena: str) -> str:
    # Cifra la contraseña a SHA-256 exactamente como lo requiere el sistema
    return hashlib.sha256(contrasena.strip().encode("utf-8")).hexdigest()

class LoginSchema(BaseModel):
    email: str
    contrasena: str

class RegistroSchema(BaseModel):
    nombre: str
    email: str
    contrasena: str

@app.post("/auth/registro")
def registrar(data: RegistroSchema):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        email_clean = data.email.strip().lower()
        
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email_clean,))
        if cursor.fetchone():
            db.close()
            return {"ok": False, "mensaje": "Ese correo ya está registrado."}

        # Ciframos la contraseña antes de guardarla en MySQL
        pwd_cifrada = cifrar_contrasena(data.contrasena)

        cursor.execute(
            "INSERT INTO usuarios (nombre, email, contrasena, rol) VALUES (%s, %s, %s, 'usuario')",
            (data.nombre.strip(), email_clean, pwd_cifrada)
        )
        db.commit()
        db.close()
        return {"ok": True, "mensaje": "Cuenta creada correctamente."}
    except Exception as e:
        db.close()
        return {"ok": False, "mensaje": f"Error en el servidor: {str(e)}"}

@app.post("/auth/login")
def login(data: LoginSchema):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    email_clean = data.email.strip().lower()
    # Convertimos la contraseña ingresada a SHA-256 para compararla en la BD
    pwd_cifrada = cifrar_contrasena(data.contrasena)

    cursor.execute(
        "SELECT id, nombre, email, rol FROM usuarios WHERE email = %s AND contrasena = %s", 
        (email_clean, pwd_cifrada)
    )
    user = cursor.fetchone()
    db.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return user
