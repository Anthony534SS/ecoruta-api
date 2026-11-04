from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector

app = FastAPI(title="EcoRuta API")

DB_CONFIG = {
    'host': 'ecoruta-antonio-618d.c.aivencloud.com',
    'port': 21716,
    'user': 'avnadmin',
    'password': 'AVNS_Yum4uq8V_ok00akE24o',
    'database': 'ecoruta_db'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# Schema para el registro
class RegistroSchema(BaseModel):
    nombre: str
    email: str
    contrasena: str

@app.post("/auth/registro")
def registrar(data: RegistroSchema):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Formatear correo
        email_clean = data.email.strip().lower()
        
        # Verificar si ya existe
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email_clean,))
        if cursor.fetchone():
            db.close()
            return {"ok": False, "mensaje": "Ese correo ya está registrado."}

        # Insertar nuevo usuario con rol por defecto 'usuario'
        cursor.execute(
            "INSERT INTO usuarios (nombre, email, contrasena, rol) VALUES (%s, %s, %s, 'usuario')",
            (data.nombre.strip(), email_clean, data.contrasena.strip())
        )
        db.commit()
        db.close()
        return {"ok": True, "mensaje": "Cuenta creada correctamente."}
    except Exception as e:
        db.close()
        return {"ok": False, "mensaje": f"Error interno del servidor: {str(e)}"}
