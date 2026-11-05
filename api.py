import hashlib
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector

app = FastAPI(title="EcoRuta API REST")

DB_CONFIG = {
    'host': 'ecoruta-antonio-618d.c.aivencloud.com',
    'port': 21716,
    'user': 'avnadmin',
    'password': 'AVNS_Yum4uq8V_ok00akE24o',
    'database': 'ecoruta_db'  # Cambia a 'ecoruta_db' si creaste las tablas en esa BD
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def cifrar_contrasena(contrasena: str) -> str:
    return hashlib.sha256(contrasena.strip().encode("utf-8")).hexdigest()


# ---------------- SCHEMAS ----------------

class LoginSchema(BaseModel):
    email: str
    contrasena: str

class RegistroSchema(BaseModel):
    nombre: str
    email: str
    contrasena: str

class ReporteSchema(BaseModel):
    imagen: str
    latitud: float
    longitud: float
    usuario_id: int

class ActualizarEstadoSchema(BaseModel):
    estado: str

class ActualizarPerfilSchema(BaseModel):
    nombre: str
    email: str
    nueva_contrasena: Optional[str] = ""

class MensajeSchema(BaseModel):
    contenido: str
    usuario_id: int
    reporte_id: Optional[int] = None


# ---------------- AUTENTICACIÓN ----------------

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


# ---------------- REPORTES COMUNITARIOS ----------------

@app.get("/reportes")
def obtener_reportes(limite: Optional[int] = None, usuario_id: Optional[int] = None):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    sql = """
        SELECT r.id, r.imagen, r.latitud, r.longitud, r.fecha_hora, r.estado, 
               r.usuario_id, u.nombre AS usuario_nombre, u.email AS usuario_email
        FROM reportes r
        INNER JOIN usuarios u ON u.id = r.usuario_id
    """
    params = []
    
    if usuario_id:
        sql += " WHERE r.usuario_id = %s"
        params.append(usuario_id)
        
    sql += " ORDER BY r.id DESC"
    
    if limite:
        sql += " LIMIT %s"
        params.append(limite)
        
    cursor.execute(sql, tuple(params))
    reportes = cursor.fetchall()
    db.close()
    return reportes

@app.get("/reportes/{reporte_id}")
def obtener_reporte(reporte_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id, r.imagen, r.latitud, r.longitud, r.fecha_hora, r.estado, 
               r.usuario_id, u.nombre AS usuario_nombre, u.email AS usuario_email
        FROM reportes r
        INNER JOIN usuarios u ON u.id = r.usuario_id
        WHERE r.id = %s
    """, (reporte_id,))
    reporte = cursor.fetchone()
    db.close()
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return reporte

@app.post("/reportes")
def crear_reporte(data: ReporteSchema):
    db = get_db()
    cursor = db.cursor()
    fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute("""
        INSERT INTO reportes (imagen, latitud, longitud, fecha_hora, estado, usuario_id)
        VALUES (%s, %s, %s, %s, 'Pendiente', %s)
    """, (data.imagen, data.latitud, data.longitud, fecha_hora, data.usuario_id))
    db.commit()
    rid = cursor.lastrowid
    db.close()
    return {"id": rid, "mensaje": "Reporte creado exitosamente."}

@app.put("/reportes/{reporte_id}/estado")
def actualizar_estado(reporte_id: int, data: ActualizarEstadoSchema):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE reportes SET estado = %s WHERE id = %s", (data.estado, reporte_id))
    db.commit()
    db.close()
    return {"ok": True}

@app.delete("/reportes/{reporte_id}")
def eliminar_reporte(reporte_id: int, usuario_id: Optional[int] = None, es_admin: bool = False):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    if not es_admin:
        cursor.execute("SELECT usuario_id FROM reportes WHERE id = %s", (reporte_id,))
        rep = cursor.fetchone()
        if not rep or rep["usuario_id"] != usuario_id:
            db.close()
            raise HTTPException(status_code=403, detail="No tienes permisos para borrar este reporte")
            
    cursor.execute("DELETE FROM reportes WHERE id = %s", (reporte_id,))
    db.commit()
    db.close()
    return {"ok": True}


# ---------------- USUARIOS Y PERFIL ----------------

@app.get("/usuarios")
def obtener_usuarios():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.nombre, u.email, u.rol, COUNT(r.id) AS total_reportes
        FROM usuarios u
        LEFT JOIN reportes r ON r.usuario_id = u.id
        WHERE u.rol = 'usuario'
        GROUP BY u.id, u.nombre, u.email, u.rol
        ORDER BY u.nombre ASC
    """)
    usuarios = cursor.fetchall()
    db.close()
    return usuarios

@app.put("/usuarios/{usuario_id}")
def actualizar_perfil(usuario_id: int, data: ActualizarPerfilSchema):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    email_clean = data.email.strip().lower()
    
    if data.nueva_contrasena and data.nueva_contrasena.strip():
        pwd_cifrada = cifrar_contrasena(data.nueva_contrasena)
        cursor.execute("""
            UPDATE usuarios SET nombre = %s, email = %s, contrasena = %s WHERE id = %s
        """, (data.nombre.strip(), email_clean, pwd_cifrada, usuario_id))
    else:
        cursor.execute("""
            UPDATE usuarios SET nombre = %s, email = %s WHERE id = %s
        """, (data.nombre.strip(), email_clean, usuario_id))
        
    db.commit()
    
    cursor.execute("SELECT id, nombre, email, rol FROM usuarios WHERE id = %s", (usuario_id,))
    usuario_actualizado = cursor.fetchone()
    db.close()
    
    return {"ok": True, "usuario": usuario_actualizado}

@app.get("/auth/seed-admin")
def seed_admin_endpoint():
    email = "admin@ecoruta.mx"
    password_plana = "EcoRuta2026"
    nombre = "Administrador EcoRuta"
    rol = "admin"
    
    pwd_cifrada = cifrar_contrasena(password_plana)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()

    if user:
        cursor.execute(
            "UPDATE usuarios SET contrasena = %s, rol = %s WHERE email = %s",
            (pwd_cifrada, rol, email)
        )
        mensaje = "Administrador actualizado con éxito."
    else:
        cursor.execute(
            "INSERT INTO usuarios (nombre, email, contrasena, rol) VALUES (%s, %s, %s, %s)",
            (nombre, email, pwd_cifrada, rol)
        )
        mensaje = "Administrador creado con éxito."

    db.commit()
    db.close()
    return {"ok": True, "mensaje": mensaje}
