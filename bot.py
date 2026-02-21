import logging
import json
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Configuración
TOKEN = "8211219706:AAE3tN8m1u7OrV5txNiod4fwcpTlCk1FE8w"
DB_FILE = "contactos.json"
CONFIG_FILE = "config.json"

# Estados
ESPERANDO_NOMBRE, ESPERANDO_NUMERO, BUSCAR_NOMBRE, ELIMINAR_NOMBRE = range(4)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== CONFIG (ON/OFF) =====
def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"bot_activo": True, "admin_id": None}

def guardar_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

# ===== BASE DE DATOS =====
def cargar_contactos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_contactos(contactos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(contactos, f, ensure_ascii=False, indent=2)

# ===== TECLADO =====
def menu_principal(es_admin=False):
    teclado = [
        ["➕ Agregar Contacto", "🔍 Buscar Contacto"],
        ["📋 Ver Todos", "🗑️ Eliminar Contacto"]
    ]
    if es_admin:
        config = cargar_config()
        estado = "🔴 Apagar Bot" if config["bot_activo"] else "🟢 Encender Bot"
        teclado.append([estado])
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    user_id = update.effective_user.id

    if config["admin_id"] is None:
        config["admin_id"] = user_id
        guardar_config(config)

    es_admin = (user_id == config["admin_id"])

    if not config["bot_activo"] and not es_admin:
        await update.message.reply_text("⛔ El bot está desactivado en este momento.")
        return

    await update.message.reply_text(
        "👋 ¡Hola! Soy tu bot de contactos Nequi.\n\nElige una opción:",
        reply_markup=menu_principal(es_admin)
    )

# ===== MENÚ =====
async def manejar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    user_id = update.effective_user.id
    es_admin = (user_id == config["admin_id"])
    texto = update.message.text

    if texto in ["🔴 Apagar Bot", "🟢 Encender Bot"] and es_admin:
        config["bot_activo"] = not config["bot_activo"]
        guardar_config(config)
        estado = "🟢 Bot ENCENDIDO" if config["bot_activo"] else "🔴 Bot APAGADO"
        await update.message.reply_text(f"{estado}", reply_markup=menu_principal(es_admin))
        return ConversationHandler.END

    if not config["bot_activo"] and not es_admin:
        await update.message.reply_text("⛔ El bot está desactivado.")
        return ConversationHandler.END

    if texto == "➕ Agregar Contacto":
        await update.message.reply_text("📝 Escribe el *nombre* del contacto:", parse_mode="Markdown")
        return ESPERANDO_NOMBRE

    elif texto == "🔍 Buscar Contacto":
        await update.message.reply_text("🔍 Escribe el nombre a buscar:")
        return BUSCAR_NOMBRE

    elif texto == "📋 Ver Todos":
        contactos = cargar_contactos()
        if not contactos:
            await update.message.reply_text("📭 No hay contactos guardados.", reply_markup=menu_principal(es_admin))
        else:
            lista = "\n".join([f"👤 *{c['nombre']}* — `{c['nequi']}`" for c in contactos])
            await update.message.reply_text(f"📋 *Contactos:*\n\n{lista}", parse_mode="Markdown", reply_markup=menu_principal(es_admin))
        return ConversationHandler.END

    elif texto == "🗑️ Eliminar Contacto":
        await update.message.reply_text("🗑️ Escribe el nombre del contacto a eliminar:")
        return ELIMINAR_NOMBRE

# ===== AGREGAR =====
async def recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text
    await update.message.reply_text("📱 Escribe el número de *Nequi*:", parse_mode="Markdown")
    return ESPERANDO_NUMERO

async def recibir_numero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    numero = update.message.text
    nombre = context.user_data.get("nombre")
    config = cargar_config()
    es_admin = (update.effective_user.id == config["admin_id"])

    contactos = cargar_contactos()
    contactos.append({"nombre": nombre, "nequi": numero})
    guardar_contactos(contactos)

    await update.message.reply_text(
        f"✅ Contacto guardado:\n👤 *{nombre}*\n📱 `{numero}`",
        parse_mode="Markdown",
        reply_markup=menu_principal(es_admin)
    )
    return ConversationHandler.END

# ===== BUSCAR =====
async def buscar_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    es_admin = (update.effective_user.id == config["admin_id"])
    nombre_buscar = update.message.text.lower()
    contactos = cargar_contactos()
    resultados = [c for c in contactos if nombre_buscar in c["nombre"].lower()]

    if resultados:
        lista = "\n".join([f"👤 *{c['nombre']}* — `{c['nequi']}`" for c in resultados])
        await update.message.reply_text(f"🔍 *Resultados:*\n\n{lista}", parse_mode="Markdown", reply_markup=menu_principal(es_admin))
    else:
        await update.message.reply_text("❌ No se encontró ningún contacto.", reply_markup=menu_principal(es_admin))

    return ConversationHandler.END

# ===== ELIMINAR =====
async def eliminar_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    es_admin = (update.effective_user.id == config["admin_id"])
    nombre_eliminar = update.message.text.lower()
    contactos = cargar_contactos()
    nuevos = [c for c in contactos if nombre_eliminar not in c["nombre"].lower()]

    if len(nuevos) < len(contactos):
        guardar_contactos(nuevos)
        await update.message.reply_text("✅ Contacto eliminado.", reply_markup=menu_principal(es_admin))
    else:
        await update.message.reply_text("❌ No se encontró ese contacto.", reply_markup=menu_principal(es_admin))

    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    es_admin = (update.effective_user.id == config["admin_id"])
    await update.message.reply_text("❌ Cancelado.", reply_markup=menu_principal(es_admin))
    return ConversationHandler.END

# ===== MAIN =====
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_menu)],
        states={
            ESPERANDO_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre)],
            ESPERANDO_NUMERO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_numero)],
            BUSCAR_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_contacto)],
            ELIMINAR_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, eliminar_contacto)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("🤖 Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
