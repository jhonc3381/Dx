import logging
import json
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8211219706:AAE3tN8m1u7OrV5txNiod4fwcpTlCk1FE8w"
DB_FILE = "contactos.json"
CONFIG_FILE = "config.json"

ESPERANDO_NOMBRE, ESPERANDO_NUMERO, BUSCAR_NOMBRE, ELIMINAR_NOMBRE = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"bot_activo": True, "admin_id": None}

def guardar_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def cargar_contactos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_contactos(contactos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(contactos, f, ensure_ascii=False, indent=2)

def get_menu(es_admin=False):
    config = cargar_config()
    botones = [
        [KeyboardButton("➕ Agregar Contacto"), KeyboardButton("🔍 Buscar Contacto")],
        [KeyboardButton("📋 Ver Todos"), KeyboardButton("🗑️ Eliminar Contacto")]
    ]
    if es_admin:
        estado = "🔴 Apagar Bot" if config["bot_activo"] else "🟢 Encender Bot"
        botones.append([KeyboardButton(estado)])
    return ReplyKeyboardMarkup(botones, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    user_id = update.effective_user.id
    if config["admin_id"] is None:
        config["admin_id"] = user_id
        guardar_config(config)
    es_admin = (user_id == config["admin_id"])
    if not config["bot_activo"] and not es_admin:
        await update.message.reply_text("⛔ El bot está desactivado.")
        return
    await update.message.reply_text(
        "👋 ¡Hola! Soy tu bot de contactos Nequi.\nElige una opción:",
        reply_markup=get_menu(es_admin)
    )

async def manejar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    user_id = update.effective_user.id
    es_admin = (user_id == config["admin_id"])
    texto = update.message.text

    if texto in ["🔴 Apagar Bot", "🟢 Encender Bot"] and es_admin:
        config["bot_activo"] = not config["bot_activo"]
        guardar_config(config)
        estado = "🟢 Bot ENCENDIDO" if config["bot_activo"] else "🔴 Bot APAGADO"
        await update.message.reply_text(estado, reply_markup=get_menu(es_admin))
        return ConversationHandler.END

    if not config["bot_activo"] and not es_admin:
        await update.message.reply_text("⛔ El bot está desactivado.")
        return ConversationHandler.END

    if texto == "➕ Agregar Contacto":
        await update.message.reply_text("📝 Escribe el nombre del contacto:")
        return ESPERANDO_NOMBRE
    elif texto == "🔍 Buscar Contacto":
        await update.message.reply_text("🔍 Escribe el nombre a buscar:")
        return BUSCAR_NOMBRE
    elif texto == "📋 Ver Todos":
        contactos = cargar_contactos()
        if not contactos:
            await update.message.reply_text("📭 No hay contactos.", reply_markup=get_menu(es_admin))
        else:
            lista = "\n".join([f"👤 {c['nombre']} — {c['nequi']}" for c in contactos])
            await update.message.reply_text(f"📋 Contactos:\n\n{lista}", reply_markup=get_menu(es_admin))
        return ConversationHandler.END
    elif texto == "🗑️ Eliminar Contacto":
        await update.message.reply_text("🗑️ Escribe el nombre a eliminar:")
        return ELIMINAR_NOMBRE

async def recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text
    await update.message.reply_text("📱 Escribe el número de Nequi:")
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
        f"✅ Guardado:\n👤 {nombre}\n📱 {numero}",
        reply_markup=get_menu(es_admin)
    )
    return ConversationHandler.END

async def buscar_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    es_admin = (update.effective_user.id == config["admin_id"])
    nombre_buscar = update.message.text.lower()
    contactos = cargar_contactos()
    resultados = [c for c in contactos if nombre_buscar in c["nombre"].lower()]
    if resultados:
        lista = "\n".join([f"👤 {c['nombre']} — {c['nequi']}" for c in resultados])
        await update.message.reply_text(f"🔍 Resultados:\n\n{lista}", reply_markup=get_menu(es_admin))
    else:
        await update.message.reply_text("❌ No encontrado.", reply_markup=get_menu(es_admin))
    return ConversationHandler.END

async def eliminar_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    es_admin = (update.effective_user.id == config["admin_id"])
    nombre_eliminar = update.message.text.lower()
    contactos = cargar_contactos()
    nuevos = [c for c in contactos if nombre_eliminar not in c["nombre"].lower()]
    if len(nuevos) < len(contactos):
        guardar_contactos(nuevos)
        await update.message.reply_text("✅ Eliminado.", reply_markup=get_menu(es_admin))
    else:
        await update.message.reply_text("❌ No encontrado.", reply_markup=get_menu(es_admin))
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cargar_config()
    es_admin = (update.effective_user.id == config["admin_id"])
    await update.message.reply_text("❌ Cancelado.", reply_markup=get_menu(es_admin))
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
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
    app.add_handler(conv)
    logger.info("Bot iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
