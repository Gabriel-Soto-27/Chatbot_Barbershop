const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const axios = require("axios");
const express = require("express");

// ─────────────────────────────────────────────
// CONFIGURACIÓN
// ─────────────────────────────────────────────

// Número del barbero (incluir código de país, sin + ni espacios)
// Ejemplo: si el número es +52 844 123 4567 → "528441234567@c.us"
const NUMERO_BARBERO = "528715690592@c.us";

// URL de la API Python
const API_PYTHON = "http://127.0.0.1:5000/mensaje";

// ─────────────────────────────────────────────
// CLIENTE DE WHATSAPP
// ─────────────────────────────────────────────

const client = new Client({
  authStrategy: new LocalAuth(), // Guarda la sesión para no escanear QR cada vez
  puppeteer: {
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
});

// Mostrar QR en la terminal para escanear con WhatsApp
client.on("qr", (qr) => {
  console.log("\n📱 Escanea este QR con tu WhatsApp:\n");
  qrcode.generate(qr, { small: true });
});

client.on("ready", () => {
  console.log("✅ WhatsApp conectado y bot listo!");
});

client.on("auth_failure", () => {
  console.error("❌ Error de autenticación. Borra la carpeta .wwebjs_auth y vuelve a intentarlo.");
});

// ─────────────────────────────────────────────
// RECIBIR MENSAJES DE CLIENTES
// ─────────────────────────────────────────────

client.on("message", async (message) => {
  // Ignorar mensajes del propio bot, grupos y estados
  if (message.fromMe) return;
  if (message.from === "status@broadcast") return;
  if (message.from.includes("@g.us")) return; // Ignorar grupos

  const clienteId = message.from; // Número del cliente, ej: "528441234567@c.us"
  const texto = message.body.trim();

  if (!texto) return; // Ignorar mensajes sin texto (imágenes, stickers, audios, etc.)

  console.log(`📨 Mensaje de ${clienteId}: ${texto}`);

  try {
    // Enviar mensaje a la API Python y obtener respuesta del bot
    const response = await axios.post(API_PYTHON, {
      cliente_id: clienteId,
      mensaje: texto,
    });

    const respuesta = response.data.respuesta;
    await message.reply(respuesta);
    console.log(`🤖 Bot respondió a ${clienteId}`);
  } catch (error) {
    console.error("❌ Error al contactar la API Python:", error.message);
    await message.reply(
      "Lo sentimos, estamos teniendo problemas técnicos. Por favor intenta de nuevo en unos momentos."
    );
  }
});

// ─────────────────────────────────────────────
// SERVIDOR EXPRESS: RECIBIR NOTIFICACIONES DESDE PYTHON
// ─────────────────────────────────────────────

const app = express();
app.use(express.json());

app.post("/notificar", async (req, res) => {
  const { mensaje } = req.body;
  if (!mensaje) {
    return res.status(400).json({ error: "Falta el mensaje" });
  }
  try {
    const numeroLimpio = NUMERO_BARBERO.replace("@c.us", "");
    const numberId = await client.getNumberId(numeroLimpio);
    if (!numberId) {
      console.error("❌ No se encontró el número del barbero en WhatsApp");
      return res.status(500).json({ error: "Número no encontrado" });
    }
    await client.sendMessage(numberId._serialized, mensaje);
    console.log("🔔 Notificación enviada al barbero");
    res.json({ ok: true });
  } catch (error) {
    console.error("❌ Error al enviar notificación al barbero:", error.message);
    res.status(500).json({ error: "No se pudo enviar la notificación" });
  }
});

app.listen(3000, () => {
  console.log("🚀 Servidor de notificaciones corriendo en http://localhost:3000");
});

// ─────────────────────────────────────────────
// INICIAR WHATSAPP
// ─────────────────────────────────────────────

client.initialize();
