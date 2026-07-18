import sqlite3
from datetime import datetime, timedelta

DB_PATH = "barberia.db"

# ─────────────────────────────────────────────
# SERVICIOS Y HORARIOS
# ─────────────────────────────────────────────

SERVICIOS = {
    "1": ("Desvanecido con navaja", 150),
    "2": ("Desvanecido con cero", 140),
    "3": ("Corte clásico", 130),
    "4": ("Barba más pigmento", 100),
    "5": ("Barba", 80),
    "6": ("Pigmento", 30),
    "7": ("Ceja", 30),
}

HORARIOS_DISPONIBLES = [
    "11:00", "12:00", "13:00", "14:00",
    "15:00", "16:00", "17:00", "18:00"
]

DIAS_LABORALES = [0, 1, 2, 3, 4, 5]  # Lunes=0 ... Sábado=5 (Domingo=6 cerrado)


# ─────────────────────────────────────────────
# INICIALIZACIÓN DE LA BASE DE DATOS
# ─────────────────────────────────────────────

def inicializar_db():
    """Crea la tabla de citas si no existe."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL,
            servicios TEXT NOT NULL,
            total REAL NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            estado TEXT DEFAULT 'activa'
        )
    """)
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# CALENDARIO: 3 DÍAS HÁBILES DISPONIBLES
# ─────────────────────────────────────────────

def obtener_dias_disponibles():
    """
    Retorna los próximos 3 días hábiles (lunes-sábado) a partir de hoy,
    saltando domingos automáticamente.
    """
    dias = []
    dia = datetime.now().date()
    while len(dias) < 3:
        if dia.weekday() != 6:  # 6 = domingo
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def formatear_calendario():
    """Muestra los 3 días hábiles disponibles numerados para que el cliente elija."""
    dias = obtener_dias_disponibles()
    NOMBRES_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    lineas = []
    for i, d in enumerate(dias, 1):
        nombre_dia = NOMBRES_DIAS[d.weekday()]
        lineas.append(f"{i}️⃣ {nombre_dia} {d.strftime('%d/%m/%Y')}")
    return "\n".join(lineas), dias


# ─────────────────────────────────────────────
# NORMALIZACIÓN DE HORA
# ─────────────────────────────────────────────

def normalizar_hora(hora_str):
    """
    Acepta formatos como '11', '11:00', '11am', '13', '13:00'.
    Retorna el formato estándar 'HH:00' o None si no es válido.
    """
    hora_str = hora_str.strip().lower().replace("am", "").replace("pm", "").strip()
    # Quitar los minutos si vienen con ':'
    if ":" in hora_str:
        hora_str = hora_str.split(":")[0]
    if hora_str.isdigit():
        hora_fmt = f"{int(hora_str):02d}:00"
        if hora_fmt in HORARIOS_DISPONIBLES:
            return hora_fmt
    return None


# ─────────────────────────────────────────────
# VALIDACIONES
# ─────────────────────────────────────────────

def es_fecha_valida_en_calendario(opcion_str, dias_disponibles):
    """
    Valida que la opción elegida (1, 2 o 3) corresponda a un día del calendario.
    Retorna (True, fecha_str) o (False, mensaje_error).
    """
    if not opcion_str.isdigit():
        return False, "Por favor escribe 1, 2 o 3 para elegir el día."
    opcion = int(opcion_str)
    if opcion < 1 or opcion > len(dias_disponibles):
        return False, f"Opción inválida. Elige entre 1 y {len(dias_disponibles)}."
    fecha = dias_disponibles[opcion - 1]
    return True, fecha.strftime("%d/%m/%Y")


def horario_disponible(fecha_str, hora):
    """Verifica si el horario está libre en la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM citas
        WHERE fecha = ? AND hora = ? AND estado = 'activa'
    """, (fecha_str, hora))
    resultado = cursor.fetchone()
    conn.close()
    return resultado is None


def horarios_libres(fecha_str):
    """Retorna lista de horarios disponibles en una fecha."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT hora FROM citas
        WHERE fecha = ? AND estado = 'activa'
    """, (fecha_str,))
    ocupados = {row[0] for row in cursor.fetchall()}
    conn.close()
    return [h for h in HORARIOS_DISPONIBLES if h not in ocupados]


# ─────────────────────────────────────────────
# OPERACIONES CRUD
# ─────────────────────────────────────────────

def agendar_cita(nombre, telefono, servicios_lista, fecha_str, hora):
    """
    Guarda una nueva cita en la base de datos.
    servicios_lista: lista de claves del diccionario SERVICIOS, ej. ["1", "5"]
    Retorna (cita_id, total, nombres_servicios).
    """
    nombres_servicios = ", ".join(SERVICIOS[s][0] for s in servicios_lista)
    total = sum(SERVICIOS[s][1] for s in servicios_lista)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO citas (nombre, telefono, servicios, total, fecha, hora, estado)
        VALUES (?, ?, ?, ?, ?, ?, 'activa')
    """, (nombre, telefono, nombres_servicios, total, fecha_str, hora))
    cita_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return cita_id, total, nombres_servicios


def cancelar_cita(cita_id):
    """Marca una cita como cancelada."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE citas SET estado = 'cancelada' WHERE id = ? AND estado = 'activa'
    """, (cita_id,))
    filas = cursor.rowcount
    conn.commit()
    conn.close()
    return filas > 0


def modificar_cita(cita_id, nueva_fecha, nueva_hora, nuevos_servicios=None):
    """
    Actualiza fecha, hora y opcionalmente los servicios de una cita activa.
    nuevos_servicios: lista de claves de SERVICIOS, ej. ["1", "5"] (opcional).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if nuevos_servicios:
        nombres = ", ".join(SERVICIOS[s][0] for s in nuevos_servicios)
        total = sum(SERVICIOS[s][1] for s in nuevos_servicios)
        cursor.execute("""
            UPDATE citas SET fecha = ?, hora = ?, servicios = ?, total = ?
            WHERE id = ? AND estado = 'activa'
        """, (nueva_fecha, nueva_hora, nombres, total, cita_id))
    else:
        cursor.execute("""
            UPDATE citas SET fecha = ?, hora = ? WHERE id = ? AND estado = 'activa'
        """, (nueva_fecha, nueva_hora, cita_id))
    filas = cursor.rowcount
    conn.commit()
    conn.close()
    return filas > 0


def buscar_cita_por_telefono(telefono):
    """Busca citas activas de un cliente por su número de teléfono."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre, servicios, total, fecha, hora
        FROM citas
        WHERE telefono = ? AND estado = 'activa'
        ORDER BY fecha, hora
    """, (telefono,))
    resultados = cursor.fetchall()
    conn.close()
    return resultados


def obtener_cita_por_id(cita_id):
    """Retorna los datos de una cita específica."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre, telefono, servicios, total, fecha, hora, estado
        FROM citas WHERE id = ?
    """, (cita_id,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado
