from flask import Flask, request, jsonify
from chatbot import procesar_mensaje
from database import inicializar_db

app = Flask(__name__)
app.config["WTF_CSRF_ENABLED"] = False

# Número del barbero (se usa desde index.js, pero lo definimos aquí también como referencia)
NUMERO_BARBERO = "528715690592@c.us"  # Ejemplo: "528441234567@c.us"

@app.route("/mensaje", methods=["POST"])
def recibir_mensaje():
    """
    Recibe un mensaje del cliente desde index.js y retorna la respuesta del bot.
    Body esperado: { "cliente_id": "...", "mensaje": "..." }
    """
    data = request.get_json()
    cliente_id = data.get("cliente_id")
    mensaje = data.get("mensaje")

    if not cliente_id or not mensaje:
        return jsonify({"error": "Faltan campos"}), 400

    respuesta = procesar_mensaje(cliente_id, mensaje)
    return jsonify({"respuesta": respuesta})


@app.route("/health", methods=["GET"])
def health():
    """Endpoint para verificar que la API está corriendo."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    inicializar_db()
    print("🚀 API del bot corriendo en http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
