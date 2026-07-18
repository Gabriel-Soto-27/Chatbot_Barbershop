from database import (
    inicializar_db, SERVICIOS, HORARIOS_DISPONIBLES,
    normalizar_hora, horario_disponible, horarios_libres,
    formatear_calendario, obtener_dias_disponibles, es_fecha_valida_en_calendario,
    agendar_cita, cancelar_cita, modificar_cita,
    buscar_cita_por_telefono, obtener_cita_por_id
)
import requests

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

# URL del servidor Node.js para enviar notificaciones al barbero
NOTIFICACIONES_URL = "http://localhost:3000/notificar"

# ─────────────────────────────────────────────
# ESTADO DE LA CONVERSACIÓN
# ─────────────────────────────────────────────

conversaciones = {}

def obtener_estado(cliente_id):
    if cliente_id not in conversaciones:
        conversaciones[cliente_id] = {"paso": "menu_principal", "datos": {}}
    return conversaciones[cliente_id]

def reiniciar_estado(cliente_id):
    conversaciones[cliente_id] = {"paso": "menu_principal", "datos": {}}


# ─────────────────────────────────────────────
# NOTIFICACIONES AL BARBERO
# ─────────────────────────────────────────────

def notificar_barbero(mensaje):
    """Envía una notificación al barbero a través de Node.js."""
    try:
        requests.post(NOTIFICACIONES_URL, json={"mensaje": mensaje}, timeout=5)
    except Exception as e:
        print(f"⚠️  No se pudo notificar al barbero: {e}")


def notif_nueva_cita(nombre, telefono, servicios_nombres, total, fecha, hora):
    return (
        f"🔔 *Nueva cita agendada*\n\n"
        f"👤 Cliente: {nombre}\n"
        f"📱 Teléfono: {telefono}\n"
        f"💈 Servicio(s): {servicios_nombres}\n"
        f"📅 Fecha: {fecha}\n"
        f"🕐 Hora: {hora}\n"
        f"💵 Total: ${total}"
    )


def notif_cita_cancelada(cita_id, nombre, servicios, fecha, hora):
    return (
        f"❌ *Cita cancelada*\n\n"
        f"🆔 ID: {cita_id}\n"
        f"👤 Cliente: {nombre}\n"
        f"💈 Servicio(s): {servicios}\n"
        f"📅 Fecha: {fecha}\n"
        f"🕐 Hora: {hora}"
    )


def notif_cita_modificada(cita_id, nombre, fecha_anterior, hora_anterior,
                           nueva_fecha, nueva_hora, servicios_anteriores,
                           nuevos_servicios_nombres=None, nuevo_total=None):
    msg = (
        f"✏️ *Cita modificada*\n\n"
        f"🆔 ID: {cita_id}\n"
        f"👤 Cliente: {nombre}\n\n"
        f"*Antes:*\n"
        f"📅 {fecha_anterior} a las {hora_anterior}\n"
        f"💈 {servicios_anteriores}\n\n"
        f"*Ahora:*\n"
        f"📅 {nueva_fecha} a las {nueva_hora}\n"
    )
    if nuevos_servicios_nombres:
        msg += f"💈 {nuevos_servicios_nombres}\n"
        msg += f"💵 Nuevo total: ${nuevo_total}"
    return msg


# ─────────────────────────────────────────────
# TEXTOS DEL BOT
# ─────────────────────────────────────────────

MENU_PRINCIPAL = """✂️ *Bienvenido* ✂️

¿Qué deseas hacer?

1️⃣ Agendar una cita
2️⃣ Cancelar una cita
3️⃣ Modificar una cita

Responde con el número de tu opción."""

MENU_SERVICIOS = """💈 *Nuestros servicios:*

1️⃣ Desvanecido con navaja — $150
2️⃣ Desvanecido con cero — $140
3️⃣ Corte clásico — $130
4️⃣ Barba más pigmento — $100
5️⃣ Barba — $80
6️⃣ Pigmento — $30
7️⃣ Ceja — $30

Escribe los números de los servicios que deseas separados por coma.
Ejemplo: *1, 5* para Desvanecido con navaja + Barba"""


def resumen_cita(nombre, servicios_nombres, total, fecha, hora):
    return (
        f"✅ *Cita confirmada*\n\n"
        f"👤 Nombre: {nombre}\n"
        f"💈 Servicio(s): {servicios_nombres}\n"
        f"📅 Fecha: {fecha}\n"
        f"🕐 Hora: {hora}\n"
        f"💵 Total a pagar: ${total}\n\n"
        f"¡Te esperamos! Si necesitas cancelar o modificar tu cita, "
        f"escríbenos y con gusto te ayudamos. 😊"
    )


def _mostrar_calendario():
    texto, dias = formatear_calendario()
    return (
        f"📅 *Fechas disponibles:*\n\n{texto}\n\n"
        f"Escribe el número del día que prefieres (1, 2 o 3):"
    ), dias


def _mostrar_horarios(fecha_str):
    libres = horarios_libres(fecha_str)
    if not libres:
        return None, []
    horarios_txt = "\n".join(f"🕐 {h}" for h in libres)
    return (
        f"Horarios disponibles para el {fecha_str}:\n{horarios_txt}\n\n"
        f"Escribe la hora que prefieres.\n"
        f"Puedes escribirla así: *13:00* o simplemente *13*"
    ), libres


# ─────────────────────────────────────────────
# LÓGICA PRINCIPAL
# ─────────────────────────────────────────────

def procesar_mensaje(cliente_id, mensaje):
    estado = obtener_estado(cliente_id)
    paso = estado["paso"]
    datos = estado["datos"]
    msg = mensaje.strip()

    # ── MENÚ PRINCIPAL ──────────────────────────────────────
    if paso == "menu_principal":
        if msg == "1":
            estado["paso"] = "agendar_nombre"
            return "Por favor, escribe tu *nombre completo*:"
        elif msg == "2":
            estado["paso"] = "cancelar_telefono"
            return "Para cancelar tu cita, escribe tu *número de teléfono*:"
        elif msg == "3":
            estado["paso"] = "modificar_telefono"
            return "Para modificar tu cita, escribe tu *número de teléfono*:"
        else:
            return MENU_PRINCIPAL

    # ── FLUJO: AGENDAR ──────────────────────────────────────
    elif paso == "agendar_nombre":
        if len(msg) < 2:
            return "Por favor escribe un nombre válido:"
        datos["nombre"] = msg.title()
        estado["paso"] = "agendar_telefono"
        return "Escribe tu *número de teléfono*:"

    elif paso == "agendar_telefono":
        if not msg.isdigit() or len(msg) < 8:
            return "Por favor escribe un número de teléfono válido (solo dígitos):"
        datos["telefono"] = msg
        estado["paso"] = "agendar_servicios"
        return MENU_SERVICIOS

    elif paso == "agendar_servicios":
        seleccion = [s.strip() for s in msg.split(",")]
        validos = [s for s in seleccion if s in SERVICIOS]
        if not validos:
            return f"Opción inválida. {MENU_SERVICIOS}"
        datos["servicios"] = validos
        resumen = ", ".join(f"{SERVICIOS[s][0]} (${SERVICIOS[s][1]})" for s in validos)
        subtotal = sum(SERVICIOS[s][1] for s in validos)
        cal_texto, dias = _mostrar_calendario()
        datos["dias_calendario"] = [d.strftime("%d/%m/%Y") for d in dias]
        estado["paso"] = "agendar_fecha"
        return (
            f"Seleccionaste:\n{resumen}\n"
            f"💵 Subtotal: ${subtotal}\n\n"
            f"{cal_texto}"
        )

    elif paso == "agendar_fecha":
        valido, resultado = es_fecha_valida_en_calendario(msg, obtener_dias_disponibles())
        if not valido:
            cal_texto, dias = _mostrar_calendario()
            datos["dias_calendario"] = [d.strftime("%d/%m/%Y") for d in dias]
            return f"❌ {resultado}\n\n{cal_texto}"
        datos["fecha"] = resultado
        texto_horarios, libres = _mostrar_horarios(resultado)
        if not texto_horarios:
            cal_texto, dias = _mostrar_calendario()
            datos["dias_calendario"] = [d.strftime("%d/%m/%Y") for d in dias]
            return f"😔 Lo sentimos, el día {resultado} está completamente lleno.\n\n{cal_texto}"
        estado["paso"] = "agendar_hora"
        return texto_horarios

    elif paso == "agendar_hora":
        hora = normalizar_hora(msg)
        if not hora:
            return "Hora inválida. Escribe una hora disponible.\nEjemplo: *13:00* o simplemente *13*"
        if not horario_disponible(datos["fecha"], hora):
            texto_horarios, _ = _mostrar_horarios(datos["fecha"])
            return f"❌ Ese horario ya está ocupado.\n\n{texto_horarios}"
        datos["hora"] = hora
        cita_id, total, servicios_nombres = agendar_cita(
            datos["nombre"], datos["telefono"],
            datos["servicios"], datos["fecha"], hora
        )
        nombre = datos["nombre"]
        telefono = datos["telefono"]
        fecha = datos["fecha"]
        # Notificar al barbero
        notificar_barbero(notif_nueva_cita(nombre, telefono, servicios_nombres, total, fecha, hora))
        reiniciar_estado(cliente_id)
        return resumen_cita(nombre, servicios_nombres, total, fecha, hora)

    # ── FLUJO: CANCELAR ─────────────────────────────────────
    elif paso == "cancelar_telefono":
        citas = buscar_cita_por_telefono(msg)
        if not citas:
            reiniciar_estado(cliente_id)
            return "❌ No encontramos citas activas con ese número.\n\n" + MENU_PRINCIPAL
        datos["telefono"] = msg
        estado["paso"] = "cancelar_seleccionar"
        lista = _formatear_lista_citas(citas)
        return f"📋 Tus citas activas:\n\n{lista}\n\nEscribe el *número de ID* de la cita que deseas cancelar:"

    elif paso == "cancelar_seleccionar":
        if not msg.isdigit():
            return "Por favor escribe el número de ID de la cita:"
        cita_id = int(msg)
        # Guardar datos de la cita antes de cancelar para la notificación
        cita = obtener_cita_por_id(cita_id)
        exito = cancelar_cita(cita_id)
        reiniciar_estado(cliente_id)
        if exito and cita:
            # cita: (id, nombre, telefono, servicios, total, fecha, hora, estado)
            notificar_barbero(notif_cita_cancelada(
                cita[0], cita[1], cita[3], cita[5], cita[6]
            ))
            return "✅ Tu cita ha sido cancelada exitosamente.\n\n" + MENU_PRINCIPAL
        else:
            return "❌ No se encontró esa cita. Verifica el ID e intenta de nuevo.\n\n" + MENU_PRINCIPAL

    # ── FLUJO: MODIFICAR ────────────────────────────────────
    elif paso == "modificar_telefono":
        citas = buscar_cita_por_telefono(msg)
        if not citas:
            reiniciar_estado(cliente_id)
            return "❌ No encontramos citas activas con ese número.\n\n" + MENU_PRINCIPAL
        datos["telefono"] = msg
        estado["paso"] = "modificar_seleccionar"
        lista = _formatear_lista_citas(citas)
        return f"📋 Tus citas activas:\n\n{lista}\n\nEscribe el *número de ID* de la cita que deseas modificar:"

    elif paso == "modificar_seleccionar":
        if not msg.isdigit():
            return "Por favor escribe el número de ID de la cita:"
        cita = obtener_cita_por_id(int(msg))
        if not cita or cita[7] != "activa":
            return "❌ No se encontró esa cita. Verifica el ID:"
        datos["cita_id"] = int(msg)
        # Guardar datos actuales para la notificación de modificación
        datos["fecha_anterior"] = cita[5]
        datos["hora_anterior"] = cita[6]
        datos["servicios_anteriores"] = cita[3]
        datos["nombre_cliente"] = cita[1]
        estado["paso"] = "modificar_que_cambiar"
        return (
            "¿Qué deseas modificar?\n\n"
            "1️⃣ Solo fecha y hora\n"
            "2️⃣ Solo servicio(s)\n"
            "3️⃣ Todo (fecha, hora y servicio)\n\n"
            "Escribe 1, 2 o 3:"
        )

    elif paso == "modificar_que_cambiar":
        if msg not in ["1", "2", "3"]:
            return "Por favor escribe 1, 2 o 3:"
        datos["modificar_opcion"] = msg
        if msg == "1":
            cal_texto, dias = _mostrar_calendario()
            datos["dias_calendario"] = [d.strftime("%d/%m/%Y") for d in dias]
            estado["paso"] = "modificar_fecha"
            return f"📅 Elige la nueva fecha:\n\n{cal_texto}"
        elif msg == "2":
            estado["paso"] = "modificar_servicios"
            return f"💈 Elige los nuevos servicios:\n\n{MENU_SERVICIOS}"
        else:
            estado["paso"] = "modificar_servicios"
            return f"💈 Primero elige los nuevos servicios:\n\n{MENU_SERVICIOS}"

    elif paso == "modificar_servicios":
        seleccion = [s.strip() for s in msg.split(",")]
        validos = [s for s in seleccion if s in SERVICIOS]
        if not validos:
            return f"Opción inválida.\n\n{MENU_SERVICIOS}"
        datos["nuevos_servicios"] = validos
        resumen = ", ".join(f"{SERVICIOS[s][0]} (${SERVICIOS[s][1]})" for s in validos)
        subtotal = sum(SERVICIOS[s][1] for s in validos)
        if datos.get("modificar_opcion") == "2":
            # Solo servicios: mantener fecha y hora actuales
            cita = obtener_cita_por_id(datos["cita_id"])
            exito = modificar_cita(datos["cita_id"], cita[5], cita[6], validos)
            if exito:
                notificar_barbero(notif_cita_modificada(
                    datos["cita_id"], datos["nombre_cliente"],
                    datos["fecha_anterior"], datos["hora_anterior"],
                    cita[5], cita[6],
                    datos["servicios_anteriores"],
                    resumen, subtotal
                ))
            reiniciar_estado(cliente_id)
            if exito:
                return (
                    f"✅ ¡Servicio(s) actualizados!\n"
                    f"💈 Nuevos servicios: {resumen}\n"
                    f"💵 Nuevo total: ${subtotal}\n\n"
                    + MENU_PRINCIPAL
                )
            else:
                return "❌ Hubo un problema. Intenta de nuevo.\n\n" + MENU_PRINCIPAL
        else:
            cal_texto, dias = _mostrar_calendario()
            datos["dias_calendario"] = [d.strftime("%d/%m/%Y") for d in dias]
            estado["paso"] = "modificar_fecha"
            return (
                f"Seleccionaste:\n{resumen}\n💵 Subtotal: ${subtotal}\n\n"
                f"📅 Ahora elige la nueva fecha:\n\n{cal_texto}"
            )

    elif paso == "modificar_fecha":
        valido, resultado = es_fecha_valida_en_calendario(msg, obtener_dias_disponibles())
        if not valido:
            cal_texto, dias = _mostrar_calendario()
            datos["dias_calendario"] = [d.strftime("%d/%m/%Y") for d in dias]
            return f"❌ {resultado}\n\n{cal_texto}"
        datos["nueva_fecha"] = resultado
        texto_horarios, libres = _mostrar_horarios(resultado)
        if not texto_horarios:
            cal_texto, dias = _mostrar_calendario()
            datos["dias_calendario"] = [d.strftime("%d/%m/%Y") for d in dias]
            return f"😔 El día {resultado} está completamente lleno.\n\n{cal_texto}"
        estado["paso"] = "modificar_hora"
        return texto_horarios

    elif paso == "modificar_hora":
        hora = normalizar_hora(msg)
        if not hora:
            return "Hora inválida. Escribe una hora disponible.\nEjemplo: *14:00* o simplemente *14*"
        if not horario_disponible(datos["nueva_fecha"], hora):
            texto_horarios, _ = _mostrar_horarios(datos["nueva_fecha"])
            return f"❌ Ese horario ya está ocupado.\n\n{texto_horarios}"
        nuevos_servicios = datos.get("nuevos_servicios")
        nuevos_servicios_nombres = None
        nuevo_total = None
        if nuevos_servicios:
            nuevos_servicios_nombres = ", ".join(SERVICIOS[s][0] for s in nuevos_servicios)
            nuevo_total = sum(SERVICIOS[s][1] for s in nuevos_servicios)
        exito = modificar_cita(datos["cita_id"], datos["nueva_fecha"], hora, nuevos_servicios)
        if exito:
            notificar_barbero(notif_cita_modificada(
                datos["cita_id"], datos["nombre_cliente"],
                datos["fecha_anterior"], datos["hora_anterior"],
                datos["nueva_fecha"], hora,
                datos["servicios_anteriores"],
                nuevos_servicios_nombres, nuevo_total
            ))
        nueva_fecha = datos["nueva_fecha"]
        reiniciar_estado(cliente_id)
        if exito:
            return (
                f"✅ ¡Cita modificada exitosamente!\n"
                f"📅 Nueva fecha: {nueva_fecha}\n"
                f"🕐 Nueva hora: {hora}\n\n"
                + MENU_PRINCIPAL
            )
        else:
            return "❌ Hubo un problema al modificar la cita. Intenta de nuevo.\n\n" + MENU_PRINCIPAL

    # ── FALLBACK ────────────────────────────────────────────
    else:
        reiniciar_estado(cliente_id)
        return MENU_PRINCIPAL


def _formatear_lista_citas(citas):
    lineas = []
    for cita in citas:
        cita_id, nombre, servicios, total, fecha, hora = cita
        lineas.append(
            f"🆔 ID: {cita_id}\n"
            f"   📅 {fecha} a las {hora}\n"
            f"   💈 {servicios}\n"
            f"   💵 Total: ${total}"
        )
    return "\n\n".join(lineas)


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA (prueba en consola)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    inicializar_db()
    print("🤖 Bot de Barbería iniciado. Escribe 'salir' para terminar.\n")
    cliente_id = "test_consola"
    print(MENU_PRINCIPAL)
    while True:
        entrada = input("Tú: ")
        if entrada.lower() == "salir":
            break
        respuesta = procesar_mensaje(cliente_id, entrada)
        print(f"\nBot: {respuesta}\n")
