from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from typing import Optional

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

class LoginSchema(BaseModel):
    email: str
    contrasena: str

class ReporteSchema(BaseModel):
    imagen: str
    latitud: float
    longitud: float
    usuario_id: int

@app.post("/auth/login")
def login(data: LoginSchema):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, email, rol FROM usuarios WHERE email = %s AND contrasena = %s", 
                   (data.email.strip().lower(), data.contrasena.strip()))
    user = cursor.fetchone()
    db.close()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return user

@app.get("/reportes")
def obtener_reportes():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id, r.imagen, r.latitud, r.longitud, r.fecha_hora, 
               r.estado, r.usuario_id, u.nombre AS usuario_nombre, u.email AS usuario_email
        FROM reportes r
        INNER JOIN usuarios u ON u.id = r.usuario_id
        ORDER BY r.id DESC
    """)
    res = cursor.fetchall()
    db.close()
    return res

@app.delete("/reportes/{reporte_id}")
def eliminar_reporte(reporte_id: int, usuario_id: int, es_admin: bool):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    if not es_admin:
        cursor.execute("SELECT usuario_id FROM reportes WHERE id = %s", (reporte_id,))
        rep = cursor.fetchone()
        if not rep or rep["usuario_id"] != usuario_id:
            db.close()
            raise HTTPException(status_code=403, detail="Sin permiso")
    
    cursor.execute("DELETE FROM reportes WHERE id = %s", (reporte_id,))
    db.commit()
    db.close()
    return {"ok": True}