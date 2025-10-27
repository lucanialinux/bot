import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import time
import pytz
import os  # <--- NUOVO: Importa il modulo OS
import sys # <--- NUOVO: Necessario se vogliamo uscire in caso di errore
from dotenv import load_dotenv # <--- NUOVA RIGA: Importa la funzione di caricamento
load_dotenv() # <--- NUOVA RIGA: Carica le variabili dal file .env (se esiste)

# Configurazione di base e log
# --------------------------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# 1. PARAMETRI ESSENZIALI (Ora letti dalle Variabili d'Ambiente)
# --------------------------------------------------------------------------
# Legge il token dalla variabile d'ambiente 'TELEGRAM_TOKEN'
TOKEN = os.environ.get('TELEGRAM_TOKEN')  # <--- MODIFICATO
# Legge l'ID Admin dalla variabile d'ambiente 'ADMIN_ID'
ADMIN_ID_STR = os.environ.get('ADMIN_ID') # <--- MODIFICATO

CHAT_ID_CANALE = -1002702418249  # ID del canale @basilicataGo

# Conversione di ADMIN_ID da stringa a intero (necessario per confronto)
try:
    if ADMIN_ID_STR:
        ADMIN_ID = int(ADMIN_ID_STR)
    else:
        ADMIN_ID = None
except ValueError:
    logger.error("La variabile d'ambiente ADMIN_ID non è un numero valido.")
    ADMIN_ID = None


# Controllo preliminare del token e admin ID
if not TOKEN:
    logger.error("ERRORE CRITICO: Variabile d'ambiente TELEGRAM_TOKEN non trovata. Uscita.")
    sys.exit(1) # Esce dal programma se il token non c'è

if not ADMIN_ID:
    logger.warning("ATTENZIONE: Variabile d'ambiente ADMIN_ID non trovata o non valida. I comandi admin non funzioneranno.")


# --------------------------------------------------------------------------
# 2. FUNZIONE PER INVIARE MESSAGGI AL CANALE
# --------------------------------------------------------------------------

async def invia_al_canale(context: ContextTypes.DEFAULT_TYPE, messaggio: str, keyboard=None):
    """Invia un messaggio al canale BasilicataGo."""
    try:
        await context.bot.send_message(
            chat_id=CHAT_ID_CANALE,
            text=messaggio,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        logger.info("Messaggio inviato al canale con successo")
        return True
    except Exception as e:
        logger.error(f"Errore nell'invio al canale: {e}")
        return False


# --------------------------------------------------------------------------
# 3. PUBBLICAZIONE AUTOMATICA QUOTIDIANA
# --------------------------------------------------------------------------

async def messaggio_quotidiano(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pubblica un messaggio automatico ogni giorno alle 9:00."""
    
    messaggio = (
        "🌅 Buongiorno Basilicata!\n\n"
        "📋 Oggi ti ricordiamo i nostri servizi:\n"
        "🏥 Servizi Salute e Orari ASL\n"
        "🌐 Portali Turistici della Basilicata\n"
        "📄 Bandi e Fondi Europei\n\n"
        "👉 Usa il bot per accedere a tutte le informazioni!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🤖 Apri Bot BasilicataGo", url="https://t.me/basilicatagobot")]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=CHAT_ID_CANALE,
            text=messaggio,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info("Messaggio quotidiano pubblicato con successo")
    except Exception as e:
        logger.error(f"Errore pubblicazione automatica: {e}")


# --------------------------------------------------------------------------
# 4. FUNZIONI DI COSTRUZIONE DELLE TASTIERE
# --------------------------------------------------------------------------

def get_reply_keyboard():
    """Tastiera permanente con il pulsante per aprire il menu."""
    keyboard = [[KeyboardButton("📋 Apri Menu BasilicataGo")]]
    return ReplyKeyboardMarkup(
        keyboard, 
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_main_menu_keyboard():
    """Menu principale con pulsanti inline."""
    keyboard = [
        [
            InlineKeyboardButton(
                "🏥 Servizi Salute", 
                callback_data='MENU_SERVIZI_SALUTE'
            )
        ],
        [
            InlineKeyboardButton(
                "⏰ Orari Ambulatori", 
                callback_data='MOSTRA_ORARI_AMBULATORI'
            )
        ],
        [
            InlineKeyboardButton(
                "🌐 Siti Utili Basilicata", 
                callback_data='MOSTRA_SITI_UTILI'
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# --------------------------------------------------------------------------
# 5. HANDLER PER IL COMANDO /START
# --------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Avvia il bot e mostra il pulsante per aprire il menu."""
    chat_id = update.effective_chat.id
    
    # Cancella il messaggio del comando /start
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Impossibile eliminare /start: {e}")
    
    # Messaggio di benvenuto con il pulsante permanente
    welcome_text = (
        "🏛️ **Benvenuto su BasilicataGo!**\n\n"
        "Il tuo assistente per servizi, orari e informazioni sulla Basilicata.\n\n"
        "👇 Premi il pulsante qui sotto per aprire il menu principale."
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        reply_markup=get_reply_keyboard(),
        parse_mode='Markdown'
    )


# --------------------------------------------------------------------------
# 6. COMANDI PER PUBBLICARE NEL CANALE (SOLO ADMIN)
# --------------------------------------------------------------------------

async def pubblica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando per pubblicare un messaggio nel canale (solo per admin)."""
    
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 **Uso del comando /pubblica**\n\n"
            "Sintassi: `/pubblica <messaggio>`\n\n"
            "Esempio:\n"
            "`/pubblica Nuovi servizi disponibili! 🎉`",
            parse_mode='Markdown'
        )
        return
    
    messaggio = " ".join(context.args)
    successo = await invia_al_canale(context, messaggio)
    
    if successo:
        await update.message.reply_text("✅ Messaggio pubblicato nel canale @basilicataGo!")
    else:
        await update.message.reply_text("❌ Errore nella pubblicazione. Verifica che il bot sia amministratore del canale.")


async def pubblica_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pubblica un messaggio con pulsante per aprire il bot nel canale."""
    
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    # MODIFICA: Messaggio semplificato senza Markdown
    messaggio = (
        "📢 Novità su BasilicataGo!\n\n"
        "Scopri tutti i servizi disponibili tramite il nostro bot:\n"
        "🏥 Servizi Salute\n"
        "⏰ Orari Ambulatori\n"
        "🌐 Siti Utili della Basilicata\n\n"
        "👇 Clicca qui sotto per iniziare!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🤖 Apri Bot BasilicataGo", url="https://t.me/basilicatagobot")]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=CHAT_ID_CANALE,
            text=messaggio,
            reply_markup=InlineKeyboardMarkup(keyboard)
            # MODIFICA: Rimosso parse_mode='Markdown'
        )
        await update.message.reply_text("✅ Messaggio con pulsante bot pubblicato!")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")


async def lista_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra le pubblicazioni automatiche attive."""
    
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        return
    
    if context.application.job_queue is None:
        await update.message.reply_text("Job queue non disponibile.")
        return
    
    jobs = context.application.job_queue.jobs()
    
    if not jobs:
        await update.message.reply_text("Nessuna pubblicazione automatica attiva.")
        return
    
    testo = "📋 **Pubblicazioni Automatiche Attive:**\n\n"
    for job in jobs:
        testo += f"• {job.name}\n"
    
    await update.message.reply_text(testo, parse_mode='Markdown')


async def ferma_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ferma una pubblicazione automatica."""
    
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("Uso: /ferma_job <nome_job>")
        return
    
    if context.application.job_queue is None:
        await update.message.reply_text("Job queue non disponibile.")
        return
    
    nome_job = context.args[0]
    jobs = context.application.job_queue.get_jobs_by_name(nome_job)
    
    if not jobs:
        await update.message.reply_text(f"Job '{nome_job}' non trovato.")
        return
    
    for job in jobs:
        job.schedule_removal()
    
    await update.message.reply_text(f"✅ Job '{nome_job}' fermato!")


async def help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra i comandi disponibili per l'admin."""
    
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        return
    
    help_text = (
        "📚 **Comandi Admin BasilicataGo**\n\n"
        "**Pubblicazione manuale:**\n"
        "`/pubblica <testo>` - Pubblica un messaggio\n"
        "`/pubblica_bot` - Pubblica messaggio con link al bot\n\n"
        "**Pubblicazioni automatiche:**\n"
        "`/lista_job` - Mostra job attivi\n"
        "`/ferma_job <nome>` - Ferma un job\n\n"
        "**Esempio:**\n"
        "`/pubblica Nuovi servizi sanitari disponibili!`"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


# --------------------------------------------------------------------------
# 7. HANDLER PER IL PULSANTE "APRI MENU"
# --------------------------------------------------------------------------

async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il click sul pulsante 'Apri Menu'."""
    
    try:
        await update.message.delete()
    except Exception:
        pass
    
    menu_text = "🏛️ **Menu BasilicataGo**\n\nSeleziona un'opzione:"
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=menu_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )


# --------------------------------------------------------------------------
# 8. HANDLER PER CANCELLARE ALTRI MESSAGGI
# --------------------------------------------------------------------------

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancella automaticamente qualsiasi altro messaggio dell'utente."""
    try:
        await update.message.delete()
    except Exception:
        pass


# --------------------------------------------------------------------------
# 9. HANDLER PER LA GESTIONE DEI PULSANTI INLINE
# --------------------------------------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce tutte le interazioni con i pulsanti inline."""
    query = update.callback_query
    await query.answer()
    
    data = query.data

    # --- TORNA AL MENU PRINCIPALE ---
    if data == 'TORNA_MENU_PRINCIPALE':
        await query.edit_message_text(
            text="🏛️ **Menu BasilicataGo**\n\nSeleziona un'opzione:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return

    # --- MENU SERVIZI SALUTE ---
    elif data == 'MENU_SERVIZI_SALUTE':
        pulsanti_salute = [
            [InlineKeyboardButton("🏥 Portale Sanità Regionale", callback_data='LINK_SANITA_REGIONALE')],
            [InlineKeyboardButton("📋 ASP Basilicata", callback_data='LINK_ASP_BASILICATA')],
            [InlineKeyboardButton("🏥 ASM Matera", callback_data='LINK_ASM_MATERA')],
            [InlineKeyboardButton("⬅️ Menu Principale", callback_data='TORNA_MENU_PRINCIPALE')]
        ]
        
        await query.edit_message_text(
            text="**🏥 SERVIZI SALUTE**\n\nScegli il servizio:",
            reply_markup=InlineKeyboardMarkup(pulsanti_salute),
            parse_mode='Markdown'
        )

    # --- GESTIONE LINK SERVIZI SALUTE ---
    elif data == 'LINK_SANITA_REGIONALE':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🏥 **Portale Sanità Regionale**\n\nhttps://www.regione.basilicata.it/sanita/",
            parse_mode='Markdown'
        )
        
    elif data == 'LINK_ASP_BASILICATA':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📋 **ASP Basilicata**\n\nhttps://www.aspbasilicata.it",
            parse_mode='Markdown'
        )
        
    elif data == 'LINK_ASM_MATERA':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🏥 **ASM Matera**\n\nhttps://www.asmbasilicata.it",
            parse_mode='Markdown'
        )

    # --- ORARI AMBULATORI ---
    elif data == 'MOSTRA_ORARI_AMBULATORI':
        nuovi_pulsanti = [
            [InlineKeyboardButton("📍 Potenza", callback_data='ORARI_POTENZA')],
            [InlineKeyboardButton("🗺️ Matera", callback_data='ORARI_MATERA')],
            [InlineKeyboardButton("⬅️ Menu Principale", callback_data='TORNA_MENU_PRINCIPALE')]
        ]
        
        await query.edit_message_text(
            text="**⏰ ORARI AMBULATORI**\n\nScegli la provincia:",
            reply_markup=InlineKeyboardMarkup(nuovi_pulsanti),
            parse_mode='Markdown'
        )
        
    # --- SITI UTILI ---
    elif data == 'MOSTRA_SITI_UTILI':
        pulsanti_siti = [
            [InlineKeyboardButton("🏛️ Regione Basilicata", callback_data='LINK_REGIONE')],
            [InlineKeyboardButton("🌍 Basilicata Turismo", callback_data='MENU_TURISMO')],
            [InlineKeyboardButton("📄 Portali Bandi", callback_data='PORTALI_BANDI')],
            [InlineKeyboardButton("⬅️ Menu Principale", callback_data='TORNA_MENU_PRINCIPALE')]
        ]
        
        await query.edit_message_text(
            text="**🌐 SITI UTILI**\n\nPortali istituzionali:",
            reply_markup=InlineKeyboardMarkup(pulsanti_siti),
            parse_mode='Markdown'
        )

    # --- LINK REGIONE BASILICATA ---
    elif data == 'LINK_REGIONE':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🏛️ **Regione Basilicata**\n\nhttps://www.regione.basilicata.it",
            parse_mode='Markdown'
        )

    # --- SOTTOMENU BASILICATA TURISMO ---
    elif data == 'MENU_TURISMO':
        pulsanti_turismo = [
            [InlineKeyboardButton("🌊 Bio del Fico", callback_data='LINK_BIODELFICO')],
            [InlineKeyboardButton("🏛️ Basilicata Turistica", callback_data='LINK_BASILICATATURISTICA')],
            [InlineKeyboardButton("⬅️ Indietro", callback_data='MOSTRA_SITI_UTILI')]
        ]
        
        await query.edit_message_text(
            text="**🌍 BASILICATA TURISMO**\n\nScegli il portale turistico:",
            reply_markup=InlineKeyboardMarkup(pulsanti_turismo),
            parse_mode='Markdown'
        )

    # --- LINK BIODELFICO ---
    elif data == 'LINK_BIODELFICO':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🌊 **Bio del Fico**\n\nhttps://biodelfico.com",
            parse_mode='Markdown'
        )

    # --- LINK BASILICATA TURISTICA ---
    elif data == 'LINK_BASILICATATURISTICA':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🏛️ **Basilicata Turistica**\n\nhttps://www.basilicataturistica.it",
            parse_mode='Markdown'
        )
        
    # --- ORARI SPECIFICI ---
    elif data == 'ORARI_POTENZA':
        pulsanti_pz = [
            [InlineKeyboardButton("📅 Vai al sito ASL", callback_data='LINK_ASP_ORARI')],
            [InlineKeyboardButton("📞 Contatti", callback_data='CONTATTI_PZ')],
            [InlineKeyboardButton("⬅️ Indietro", callback_data='MOSTRA_ORARI_AMBULATORI')]
        ]
        await query.edit_message_text(
            text="**📍 ORARI - POTENZA**\n\nConsulta gli orari degli ambulatori:",
            reply_markup=InlineKeyboardMarkup(pulsanti_pz),
            parse_mode='Markdown'
        )

    elif data == 'LINK_ASP_ORARI':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📅 **Orari ASP Basilicata**\n\nhttps://www.aspbasilicata.it",
            parse_mode='Markdown'
        )

    elif data == 'ORARI_MATERA':
        pulsanti_mt = [
            [InlineKeyboardButton("📅 Vai al sito ASM", callback_data='LINK_ASM_ORARI')],
            [InlineKeyboardButton("⬅️ Indietro", callback_data='MOSTRA_ORARI_AMBULATORI')]
        ]
        await query.edit_message_text(
            text="**🗺️ ORARI - MATERA**\n\nNumero: **0835 253111**",
            reply_markup=InlineKeyboardMarkup(pulsanti_mt),
            parse_mode='Markdown'
        )

    elif data == 'LINK_ASM_ORARI':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📅 **Orari ASM Matera**\n\nhttps://www.asmbasilicata.it",
            parse_mode='Markdown'
        )

    # --- DETTAGLI ---
    elif data == 'CONTATTI_PZ':
        await query.edit_message_text(
            text="**📞 CONTATTI - POTENZA**\n\n📱 Tel: 0971 313111\n✉️ Email: urp@aspbasilicata.it",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data='ORARI_POTENZA')]
            ]),
            parse_mode='Markdown'
        )

    elif data == 'PORTALI_BANDI':
        pulsanti_bandi = [
            [InlineKeyboardButton("📋 Bandi Regionali", callback_data='LINK_BANDI')],
            [InlineKeyboardButton("🇪🇺 Fondi Europei", callback_data='LINK_FONDI_EU')],
            [InlineKeyboardButton("⬅️ Indietro", callback_data='MOSTRA_SITI_UTILI')]
        ]
        await query.edit_message_text(
            text="**📄 PORTALI BANDI**\n\nAccedi ai bandi:",
            reply_markup=InlineKeyboardMarkup(pulsanti_bandi),
            parse_mode='Markdown'
        )

    elif data == 'LINK_BANDI':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📋 **Bandi Regionali**\n\nhttps://www.regione.basilicata.it/giunta/site/giunta/department.jsp?dep=100062&area=100240",
            parse_mode='Markdown'
        )

    elif data == 'LINK_FONDI_EU':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🇪🇺 **Fondi Europei Basilicata**\n\nhttps://www.europainbasilicata.it",
            parse_mode='Markdown'
        )


# --------------------------------------------------------------------------
# 10. FUNZIONE PRINCIPALE
# --------------------------------------------------------------------------

def main() -> None:
    """Avvia il bot con pubblicazioni automatiche."""
    # Il TOKEN è ora letto da os.environ.get('TELEGRAM_TOKEN')
    application = Application.builder().token(TOKEN).build()
    
    # Registra i comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pubblica", pubblica))
    application.add_handler(CommandHandler("pubblica_bot", pubblica_bot))
    application.add_handler(CommandHandler("lista_job", lista_job))
    application.add_handler(CommandHandler("ferma_job", ferma_job))
    application.add_handler(CommandHandler("help", help_admin))
    
    # Handler per i pulsanti
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Handler per il pulsante "Apri Menu"
    application.add_handler(MessageHandler(
        filters.Regex("^📋 Apri Menu BasilicataGo$"), 
        handle_menu_button
    ))
    
    # Handler per cancellare altri messaggi
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex("^📋 Apri Menu BasilicataGo$"), 
        handle_other_messages
    ))
    
    # ✨ PUBBLICAZIONE AUTOMATICA QUOTIDIANA ALLE 9:00
    if application.job_queue is not None:
        try:
            timezone = pytz.timezone('Europe/Rome')
            
            application.job_queue.run_daily(
                messaggio_quotidiano,
                time=time(hour=9, minute=0, tzinfo=timezone),
                name="messaggio_quotidiano"
            )
            logger.info("Bot avviato con pubblicazione automatica alle 9:00")
        except Exception as e:
            logger.error(f"Errore configurazione job_queue: {e}")
    else:
        logger.warning("Job queue non disponibile - pubblicazioni automatiche disabilitate")
    
    logger.info("Bot @basilicatagobot avviato e in ascolto...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()