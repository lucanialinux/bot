import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta
import pytz
import os
import sys
import asyncio
from dotenv import load_dotenv

# Carica le variabili
load_dotenv()

# Configurazione logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ✅ VARIABILI GLOBALI
pubblicazione_task = None
orario_pubblicazione = {'ore': 9, 'minuti': 0}
messaggi_programmati = {}  # 🆕 Per messaggi programmati

# PARAMETRI ESSENZIALI
TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_ID_STR = os.environ.get('ADMIN_ID')
CHAT_ID_CANALE = -1002702418249

try:
    ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR else None
except ValueError:
    ADMIN_ID = None

if not TOKEN:
    logger.error("ERRORE CRITICO: TOKEN non trovato")
    sys.exit(1)

if not ADMIN_ID:
    logger.warning("ADMIN_ID non trovato")

# --------------------------------------------------------------------------
# FUNZIONI BASE
# --------------------------------------------------------------------------

async def invia_al_canale(context: ContextTypes.DEFAULT_TYPE, messaggio: str, keyboard=None):
    """Invia un messaggio al canale BasilicataGo."""
    try:
        logger.info(f"📤 Tentativo invio al canale {CHAT_ID_CANALE}")
        await context.bot.send_message(
            chat_id=CHAT_ID_CANALE,
            text=messaggio,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        logger.info("✅ Messaggio inviato con successo")
        return True
    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        return False


async def messaggio_quotidiano(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pubblica messaggio quotidiano."""
    logger.info("⚡ INIZIO messaggio_quotidiano")
    logger.info(f"🕐 Orario attuale: {datetime.now(pytz.timezone('Europe/Rome')).strftime('%Y-%m-%d %H:%M:%S')}")
    
    messaggio = (
        "🌅 Buongiorno dalla Basilicata!\n\n"
        "✨ Scopri oggi le meraviglie della nostra terra:\n\n"
        "🏛️ Matera e i Sassi Patrimonio UNESCO\n"
        "🏖️ Le spiagge di Maratea e Metaponto\n"
        "🏡 Agriturismi e strutture ricettive\n"
        "🍷 Prodotti tipici lucani DOP e IGP\n\n"
        "👉 Usa il bot per esplorare tutte le destinazioni!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🤖 Apri Bot BasilicataGo", url="https://t.me/basilicatagobot")]
    ]
    
    try:
        logger.info(f"📤 Invio messaggio al canale {CHAT_ID_CANALE}")
        await context.bot.send_message(
            chat_id=CHAT_ID_CANALE,
            text=messaggio,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info("✅ Messaggio quotidiano pubblicato con successo")
    except Exception as e:
        logger.error(f"❌ Errore pubblicazione automatica: {e}")


# ✅ SISTEMA PUBBLICAZIONE AUTOMATICA SENZA JOB_QUEUE
async def loop_pubblicazione_quotidiana(application):
    """Loop pubblicazione automatica."""
    timezone = pytz.timezone('Europe/Rome')
    
    while True:
        try:
            now = datetime.now(timezone)
            ore = orario_pubblicazione['ore']
            minuti = orario_pubblicazione['minuti']
            
            target = now.replace(hour=ore, minute=minuti, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            
            attesa = (target - now).total_seconds()
            logger.info(f"⏰ Prossima pubblicazione: {target.strftime('%d/%m/%Y %H:%M:%S')}")
            logger.info(f"⏳ Attesa di {attesa/3600:.1f} ore")
            
            await asyncio.sleep(attesa)
            
            logger.info("📤 Pubblicazione automatica in corso...")
            
            # Crea context temporaneo
            class TempContext:
                def __init__(self, app):
                    self.bot = app.bot
                    self.application = app
            
            await messaggio_quotidiano(TempContext(application))
            
            logger.info("✅ Pubblicazione completata")
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("⏸️ Loop pubblicazione fermato")
            break
        except Exception as e:
            logger.error(f"❌ Errore nel loop pubblicazione: {e}")
            await asyncio.sleep(300)


def get_reply_keyboard():
    """Tastiera permanente con il pulsante per aprire il menu."""
    keyboard = [[KeyboardButton("🏛️ Scopri la Basilicata")]]
    return ReplyKeyboardMarkup(
        keyboard, 
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_main_menu_keyboard():
    """Menu principale con pulsanti inline."""
    keyboard = [
        [InlineKeyboardButton("🏖️ Dove Dormire", callback_data='MENU_DOVE_DORMIRE')],
        [InlineKeyboardButton("🗺️ Cosa Vedere", callback_data='MENU_COSA_VEDERE')],
        [InlineKeyboardButton("🍷 Prodotti Lucani", callback_data='MENU_PRODOTTI_LUCANI')],
        [InlineKeyboardButton("📋 Servizi BasilicataGo", callback_data='MENU_SERVIZI_BASILICATAGO')]
    ]
    return InlineKeyboardMarkup(keyboard)


# --------------------------------------------------------------------------
# COMANDI
# --------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Avvia il bot e mostra il pulsante per aprire il menu."""
    welcome_text = (
        "🏛️ **Benvenuto su BasilicataGo!**\n\n"
        "Scopri le meraviglie della Basilicata:\n\n"
        "🏖️ Strutture ricettive e soggiorni\n"
        "🗺️ Luoghi da visitare e borghi storici\n"
        "🍷 Prodotti tipici e gastronomia lucana\n"
        "📢 Annunci e opportunità locali\n\n"
        "👇 Premi il pulsante per iniziare l'esplorazione!"
    )
    
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=get_reply_keyboard(),
        parse_mode='Markdown'
    )


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
            "`/pubblica Nuova struttura ricettiva disponibile! 🏡`",
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
    
    messaggio = (
        "✨ **Scopri la Basilicata con BasilicataGo!**\n\n"
        "🏖️ Trova dove dormire (hotel, B&B, agriturismi)\n"
        "🗺️ Esplora le destinazioni più belle\n"
        "🍷 Acquista prodotti tipici lucani\n"
        "📢 Consulta annunci e servizi locali\n\n"
        "👇 Inizia subito la tua esperienza!"
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
        await update.message.reply_text("✅ Messaggio con pulsante bot pubblicato!")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")


async def test_canale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🔍 Testa l'invio immediato al canale (solo per admin)."""
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    await update.message.reply_text("📤 Invio messaggio di test al canale...")
    
    try:
        await messaggio_quotidiano(context)
        await update.message.reply_text("✅ Messaggio di test inviato al canale @basilicataGo!")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore durante l'invio: {e}")
        logger.error(f"Errore test_canale: {e}")


# 🆕 COMANDO PROGRAMMA MESSAGGIO
async def programma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📅 Programma un messaggio per una data/ora specifica.
    
    Uso: /programma GG/MM/AAAA HH:MM <messaggio>
    Esempio: /programma 30/10/2025 15:30 Evento speciale domani! 🎉
    """
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "📅 **Programma Messaggio**\n\n"
            "**Sintassi:**\n"
            "`/programma GG/MM/AAAA HH:MM <messaggio>`\n\n"
            "**Esempi:**\n"
            "`/programma 30/10/2025 15:30 Evento speciale! 🎉`\n"
            "`/programma 01/11/2025 09:00 Buon mese di novembre!`\n"
            "`/programma 05/11/2025 18:00 Nuove offerte su BasilicataGo!`",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Parse data e ora
        data_str = context.args[0]  # 30/10/2025
        ora_str = context.args[1]    # 15:30
        messaggio = " ".join(context.args[2:])  # Resto del messaggio
        
        # Converti in datetime
        timezone = pytz.timezone('Europe/Rome')
        giorno, mese, anno = map(int, data_str.split('/'))
        ore, minuti = map(int, ora_str.split(':'))
        
        data_programmata = datetime(anno, mese, giorno, ore, minuti, tzinfo=timezone)
        now = datetime.now(timezone)
        
        # Verifica che sia nel futuro
        if data_programmata <= now:
            await update.message.reply_text(
                "❌ **Data/ora già passata!**\n\n"
                f"Ora attuale: {now.strftime('%d/%m/%Y %H:%M')}\n"
                f"Data richiesta: {data_programmata.strftime('%d/%m/%Y %H:%M')}\n\n"
                "Specifica una data futura.",
                parse_mode='Markdown'
            )
            return
        
        # Calcola attesa
        attesa = (data_programmata - now).total_seconds()
        
        # Crea task per inviare il messaggio
        async def invia_programmato():
            try:
                logger.info(f"⏳ Attesa di {attesa} secondi per messaggio programmato...")
                await asyncio.sleep(attesa)
                
                logger.info(f"📤 Invio messaggio programmato: {messaggio[:50]}")
                
                keyboard = [[InlineKeyboardButton("🤖 Apri Bot BasilicataGo", url="https://t.me/basilicatagobot")]]
                
                await context.bot.send_message(
                    chat_id=CHAT_ID_CANALE,
                    text=messaggio,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                logger.info(f"✅ Messaggio programmato inviato con successo!")
                
            except asyncio.CancelledError:
                logger.info(f"⏸️ Messaggio programmato cancellato")
            except Exception as e:
                logger.error(f"❌ Errore invio programmato: {e}")
        
        # Avvia task
        task_id = f"msg_{int(datetime.now().timestamp())}"
        messaggi_programmati[task_id] = {
            'task': asyncio.create_task(invia_programmato()),
            'data': data_programmata,
            'messaggio': messaggio[:100]
        }
        
        await update.message.reply_text(
            f"✅ **Messaggio Programmato!**\n\n"
            f"📅 **Data:** {data_str}\n"
            f"🕐 **Ora:** {ora_str}\n"
            f"📝 **Messaggio:** {messaggio[:100]}{'...' if len(messaggio) > 100 else ''}\n\n"
            f"🆔 **ID:** `{task_id}`\n"
            f"⏳ **Invio tra:** {int(attesa/3600)} ore e {int((attesa%3600)/60)} minuti\n\n"
            f"Usa `/lista_programmati` per vedere tutti i messaggi programmati\n"
            f"Usa `/cancella_programmato {task_id}` per cancellare",
            parse_mode='Markdown'
        )
        logger.info(f"✅ Messaggio programmato per {data_programmata} (ID: {task_id})")
        
    except ValueError as ve:
        await update.message.reply_text(
            "❌ **Formato non valido!**\n\n"
            "Usa: `/programma GG/MM/AAAA HH:MM <messaggio>`\n\n"
            "Esempio: `/programma 30/10/2025 15:30 Il tuo messaggio qui`",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")
        logger.error(f"Errore programma: {e}")


async def lista_programmati(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📋 Mostra tutti i messaggi programmati."""
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if not messaggi_programmati:
        await update.message.reply_text(
            "📋 **Nessun messaggio programmato**\n\n"
            "Usa `/programma` per programmarne uno!",
            parse_mode='Markdown'
        )
        return
    
    timezone = pytz.timezone('Europe/Rome')
    now = datetime.now(timezone)
    
    testo = "📋 **Messaggi Programmati:**\n\n"
    
    for task_id, info in messaggi_programmati.items():
        task = info['task']
        data = info['data']
        messaggio = info['messaggio']
        
        # Calcola tempo rimanente
        if not task.done():
            rimanente = (data - now).total_seconds()
            ore_rimanenti = int(rimanente / 3600)
            minuti_rimanenti = int((rimanente % 3600) / 60)
            status = f"⏳ Tra {ore_rimanenti}h {minuti_rimanenti}m"
        else:
            status = "✅ Inviato"
        
        testo += (
            f"**ID:** `{task_id}`\n"
            f"📅 {data.strftime('%d/%m/%Y %H:%M')}\n"
            f"📝 {messaggio}...\n"
            f"{status}\n\n"
        )
    
    testo += "\nUsa `/cancella_programmato <id>` per cancellare"
    
    await update.message.reply_text(testo, parse_mode='Markdown')


async def cancella_programmato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🗑️ Cancella un messaggio programmato."""
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Uso:** `/cancella_programmato <id>`\n\n"
            "Usa `/lista_programmati` per vedere tutti gli ID",
            parse_mode='Markdown'
        )
        return
    
    task_id = context.args[0]
    
    if task_id not in messaggi_programmati:
        await update.message.reply_text(
            f"❌ **ID `{task_id}` non trovato**\n\n"
            "Usa `/lista_programmati` per vedere gli ID disponibili",
            parse_mode='Markdown'
        )
        return
    
    info = messaggi_programmati[task_id]
    task = info['task']
    
    if not task.done():
        task.cancel()
        status_msg = "✅ Messaggio programmato cancellato!"
    else:
        status_msg = "ℹ️ Messaggio già inviato, rimosso dalla lista"
    
    del messaggi_programmati[task_id]
    
    await update.message.reply_text(
        f"{status_msg}\n\n"
        f"**ID:** `{task_id}`\n"
        f"📝 {info['messaggio']}",
        parse_mode='Markdown'
    )
    logger.info(f"🗑️ Messaggio programmato {task_id} cancellato")


async def imposta_orario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """⏰ Imposta un nuovo orario per la pubblicazione automatica - SENZA JOB_QUEUE"""
    global pubblicazione_task, orario_pubblicazione
    
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "⏰ **Imposta Orario Pubblicazione**\n\n"
            "**Sintassi:** `/imposta_orario HH:MM`\n\n"
            "**Esempi:**\n"
            "`/imposta_orario 09:00` - Ore 9:00\n"
            "`/imposta_orario 14:30` - Ore 14:30\n"
            "`/imposta_orario 18:00` - Ore 18:00",
            parse_mode='Markdown'
        )
        return
    
    try:
        orario_str = context.args[0]
        ore, minuti = map(int, orario_str.split(':'))
        
        if not (0 <= ore <= 23 and 0 <= minuti <= 59):
            raise ValueError("Orario non valido")
        
        # Aggiorna l'orario
        orario_pubblicazione['ore'] = ore
        orario_pubblicazione['minuti'] = minuti
        
        # Riavvia il task
        if pubblicazione_task and not pubblicazione_task.done():
            pubblicazione_task.cancel()
            try:
                await pubblicazione_task
            except asyncio.CancelledError:
                pass
        
        pubblicazione_task = asyncio.create_task(
            loop_pubblicazione_quotidiana(context.application)
        )
        
        timezone = pytz.timezone('Europe/Rome')
        now = datetime.now(timezone)
        prossimo_invio = now.replace(hour=ore, minute=minuti, second=0, microsecond=0)
        
        if prossimo_invio <= now:
            prossimo_invio += timedelta(days=1)
        
        await update.message.reply_text(
            f"✅ **Orario aggiornato!**\n\n"
            f"📅 Pubblicazione quotidiana impostata alle **{ore:02d}:{minuti:02d}**\n"
            f"🕐 Prossimo invio: **{prossimo_invio.strftime('%d/%m/%Y alle %H:%M')}**",
            parse_mode='Markdown'
        )
        logger.info(f"✅ Orario pubblicazione aggiornato a {ore:02d}:{minuti:02d}")
        
    except ValueError:
        await update.message.reply_text(
            "❌ **Formato orario non valido!**\n\n"
            "Usa il formato `HH:MM` (24 ore)\n"
            "Esempio: `/imposta_orario 09:00`",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")
        logger.error(f"Errore imposta_orario: {e}")


async def stato_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📊 Mostra lo stato completo del bot e delle pubblicazioni."""
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    try:
        timezone = pytz.timezone('Europe/Rome')
        ora_attuale = datetime.now(timezone)
        
        # Verifica connessione al canale
        try:
            chat_info = await context.bot.get_chat(CHAT_ID_CANALE)
            canale_ok = f"✅ Connesso: @{chat_info.username or 'basilicataGo'}"
        except Exception as e:
            canale_ok = f"❌ Errore connessione: {str(e)[:50]}"
        
        # Calcola prossima pubblicazione
        ore = orario_pubblicazione['ore']
        minuti = orario_pubblicazione['minuti']
        prossimo = ora_attuale.replace(hour=ore, minute=minuti, second=0, microsecond=0)
        if prossimo <= ora_attuale:
            prossimo += timedelta(days=1)
        
        task_status = "✅ Attivo" if pubblicazione_task and not pubblicazione_task.done() else "❌ Non attivo"
        
        # Conta messaggi programmati
        programmati_attivi = sum(1 for info in messaggi_programmati.values() if not info['task'].done())
        
        stato = (
            "📊 **STATO BOT BASILICATAGO**\n\n"
            f"🕐 **Ora attuale:** {ora_attuale.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"🌐 **Timezone:** Europe/Rome\n\n"
            f"📢 **Canale:** {canale_ok}\n"
            f"🆔 ID: `{CHAT_ID_CANALE}`\n\n"
            f"⏰ **Pubblicazione automatica:** {task_status}\n"
            f"🕐 Orario: {ore:02d}:{minuti:02d}\n"
            f"📅 Prossimo: {prossimo.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"📨 **Messaggi programmati:** {programmati_attivi} attivi\n\n"
            f"👤 **Admin ID:** `{ADMIN_ID}`"
        )
        
        await update.message.reply_text(stato, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Errore nel recupero stato: {e}")
        logger.error(f"Errore stato_bot: {e}")


async def verifica_permessi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🔐 Verifica i permessi del bot nel canale."""
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    try:
        await update.message.reply_text("🔍 Verifica permessi in corso...")
        
        chat = await context.bot.get_chat(CHAT_ID_CANALE)
        bot_member = await context.bot.get_chat_member(CHAT_ID_CANALE, context.bot.id)
        
        permessi = []
        if hasattr(bot_member, 'can_post_messages'):
            permessi.append(f"📝 Pubblicare messaggi: {'✅' if bot_member.can_post_messages else '❌'}")
        
        stato_permessi = (
            f"🔐 **PERMESSI BOT NEL CANALE**\n\n"
            f"📢 **Canale:** @{chat.username or 'basilicataGo'}\n"
            f"👤 **Status:** {bot_member.status}\n\n"
            f"**Permessi:**\n" + "\n".join(permessi)
        )
        
        await update.message.reply_text(stato_permessi, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ **Errore verifica permessi**\n\n"
            f"Errore: `{str(e)}`\n\n"
            f"💡 Assicurati che:\n"
            f"• Il bot sia amministratore del canale\n"
            f"• L'ID del canale sia corretto",
            parse_mode='Markdown'
        )
        logger.error(f"Errore verifica_permessi: {e}")


async def help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📚 Mostra i comandi disponibili per l'admin."""
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        return
    
    help_text = (
        "📚 **COMANDI ADMIN BASILICATAGO**\n\n"
        
        "**📢 Pubblicazione Manuale:**\n"
        "`/pubblica <testo>` - Pubblica messaggio\n"
        "`/pubblica_bot` - Pubblica con link bot\n"
        "`/test_canale` - Test invio immediato\n\n"
        
        "**📅 Messaggi Programmati:**\n"
        "`/programma GG/MM/AAAA HH:MM <msg>` - Programma messaggio\n"
        "`/lista_programmati` - Mostra messaggi programmati\n"
        "`/cancella_programmato <id>` - Cancella messaggio\n\n"
        
        "**⏰ Gestione Automatica:**\n"
        "`/imposta_orario HH:MM` - Cambia orario quotidiano\n"
        "`/stato_bot` - Stato completo\n"
        "`/verifica_permessi` - Controlla permessi\n\n"
        
        "**Esempi:**\n"
        "`/programma 01/11/2025 18:00 Evento speciale!`\n"
        "`/imposta_orario 09:00`"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il click sul pulsante 'Scopri la Basilicata'."""
    menu_text = "🏛️ **Esplora la Basilicata**\n\nCosa ti interessa scoprire?"
    
    await update.message.reply_text(
        text=menu_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )


async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancella automaticamente qualsiasi altro messaggio dell'utente."""
    try:
        await update.message.delete()
    except Exception:
        pass


# --------------------------------------------------------------------------
# HANDLER PER LA GESTIONE DEI PULSANTI INLINE
# --------------------------------------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce tutte le interazioni con i pulsanti inline."""
    query = update.callback_query
    await query.answer()
    
    data = query.data

    if data == 'TORNA_MENU_PRINCIPALE':
        await query.edit_message_text(
            text="🏛️ **Esplora la Basilicata**\n\nCosa ti interessa scoprire?",
            reply_markup=get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return

    elif data == 'MENU_DOVE_DORMIRE':
        pulsanti_dormire = [
            [InlineKeyboardButton("🏡 Bio del Fico - Locazione Turistica", callback_data='LINK_BIODELFICO')],
            [InlineKeyboardButton("🏨 Tutte le Strutture Ricettive", callback_data='LINK_STRUTTURE_BASILICATAGO')],
            [InlineKeyboardButton("⬅️ Menu Principale", callback_data='TORNA_MENU_PRINCIPALE')]
        ]
        
        await query.edit_message_text(
            text=(
                "**🏖️ DOVE DORMIRE IN BASILICATA**\n\n"
                "Scopri le migliori strutture ricettive della regione:\n"
                "🏡 Agriturismi e case vacanza\n"
                "🏨 Hotel e B&B\n"
                "🏛️ Dimore storiche e masserie"
            ),
            reply_markup=InlineKeyboardMarkup(pulsanti_dormire),
            parse_mode='Markdown'
        )

    elif data == 'LINK_BIODELFICO':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "🏡 **Bio del Fico - Locazione Turistica**\n\n"
                "Vivi un'esperienza autentica nella natura lucana!\n\n"
                "🌿 Immerso nel verde della Basilicata\n"
                "🏖️ A pochi km dalle spiagge più belle\n"
                "🍇 Prodotti biologici a km zero\n\n"
                "🔗 **Prenota ora:** https://biodelfico.com"
            ),
            parse_mode='Markdown'
        )

    elif data == 'LINK_STRUTTURE_BASILICATAGO':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "🏨 **Strutture Ricettive Basilicata**\n\n"
                "Trova l'alloggio perfetto su BasilicataGo:\n\n"
                "✅ Hotel, B&B, Agriturismi\n"
                "✅ Case vacanza e appartamenti\n"
                "✅ Recensioni verificate\n"
                "✅ Prenotazione diretta\n\n"
                "🔗 **Scopri tutte le strutture:** https://basilicatago.com"
            ),
            parse_mode='Markdown'
        )

    elif data == 'MENU_COSA_VEDERE':
        pulsanti_vedere = [
            [InlineKeyboardButton("🏛️ Matera e i Sassi", callback_data='DESTINAZIONE_MATERA')],
            [InlineKeyboardButton("🏖️ Maratea e le Spiagge", callback_data='DESTINAZIONE_MARATEA')],
            [InlineKeyboardButton("🏰 Borghi e Castelli", callback_data='DESTINAZIONE_BORGHI')],
            [InlineKeyboardButton("🌄 Parchi Naturali", callback_data='DESTINAZIONE_PARCHI')],
            [InlineKeyboardButton("⬅️ Menu Principale", callback_data='TORNA_MENU_PRINCIPALE')]
        ]
        
        await query.edit_message_text(
            text="**🗺️ COSA VEDERE IN BASILICATA**\n\nScegli una destinazione:",
            reply_markup=InlineKeyboardMarkup(pulsanti_vedere),
            parse_mode='Markdown'
        )

    elif data == 'DESTINAZIONE_MATERA':
        pulsanti_matera = [
            [InlineKeyboardButton("📋 Maggiori Info", callback_data='INFO_MATERA')],
            [InlineKeyboardButton("⬅️ Indietro", callback_data='MENU_COSA_VEDERE')]
        ]
        await query.edit_message_text(
            text=(
                "**🏛️ MATERA - CITTÀ DEI SASSI**\n\n"
                "Patrimonio UNESCO dal 1993\n\n"
                "✨ I Sassi Barisano e Caveoso\n"
                "⛪ Chiese rupestri\n"
                "🏺 Casa Grotta e Cisterna del Palombaro\n"
                "🎬 Location di film internazionali\n\n"
                "📍 Capitale Europea della Cultura 2019"
            ),
            reply_markup=InlineKeyboardMarkup(pulsanti_matera),
            parse_mode='Markdown'
        )

    elif data == 'INFO_MATERA':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "📋 **Informazioni su Matera**\n\n"
                "🔗 Scopri tutti i dettagli, servizi e strutture su:\n"
                "https://basilicatago.com"
            ),
            parse_mode='Markdown'
        )

    elif data == 'DESTINAZIONE_MARATEA':
        pulsanti_maratea = [
            [InlineKeyboardButton("🏖️ Spiagge", callback_data='INFO_SPIAGGE')],
            [InlineKeyboardButton("⬅️ Indietro", callback_data='MENU_COSA_VEDERE')]
        ]
        await query.edit_message_text(
            text=(
                "**🏖️ MARATEA - PERLA DEL TIRRENO**\n\n"
                "32 km di costa mozzafiato\n\n"
                "🏝️ Spiagge e calette nascoste\n"
                "⛰️ Cristo Redentore (21 metri)\n"
                "🏛️ Centro storico medievale\n"
                "🌊 Mare cristallino\n\n"
                "📍 Unica località lucana sul Mar Tirreno"
            ),
            reply_markup=InlineKeyboardMarkup(pulsanti_maratea),
            parse_mode='Markdown'
        )

    elif data == 'INFO_SPIAGGE':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "🏖️ **Le Spiagge della Basilicata**\n\n"
                "Scopri tutte le spiagge, lidi e servizi su:\n"
                "https://basilicatago.com"
            ),
            parse_mode='Markdown'
        )

    elif data == 'DESTINAZIONE_BORGHI':
        await query.edit_message_text(
            text=(
                "**🏰 BORGHI E CASTELLI**\n\n"
                "📍 **Castelmezzano** e **Pietrapertosa** - Volo dell'Angelo\n"
                "📍 **Craco** - Città fantasma\n"
                "📍 **Venosa** - Città di Orazio\n"
                "📍 **Tricarico** - Borgo arabo-normanno\n"
                "📍 **Muro Lucano** - Borgo Presepe\n\n"
                "🔗 Scopri tutti i borghi su https://basilicatago.com"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data='MENU_COSA_VEDERE')]
            ]),
            parse_mode='Markdown'
        )

    elif data == 'DESTINAZIONE_PARCHI':
        await query.edit_message_text(
            text=(
                "**🌄 PARCHI NATURALI**\n\n"
                "🌲 **Parco del Pollino** - Il più grande d'Italia\n"
                "🏔️ **Parco della Val d'Agri**\n"
                "🌊 **Riserva dei Calanchi di Montalbano Jonico**\n"
                "🦅 **Parco di Gallipoli Cognato**\n"
                "🌋 **Laghi di Monticchio** (laghi vulcanici)\n\n"
                "🔗 Itinerari e info: https://basilicatago.com"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data='MENU_COSA_VEDERE')]
            ]),
            parse_mode='Markdown'
        )

    elif data == 'MENU_PRODOTTI_LUCANI':
        pulsanti_prodotti = [
            [InlineKeyboardButton("🧀 Formaggi DOP", callback_data='PRODOTTI_FORMAGGI')],
            [InlineKeyboardButton("🥓 Salumi e Lucanica", callback_data='PRODOTTI_SALUMI')],
            [InlineKeyboardButton("🍷 Vini e Aglianico", callback_data='PRODOTTI_VINI')],
            [InlineKeyboardButton("🌶️ Peperoni Cruschi IGP", callback_data='PRODOTTI_CRUSCHI')],
            [InlineKeyboardButton("🛒 Acquista su BasilicataGo", callback_data='LINK_PRODOTTI_BASILICATAGO')],
            [InlineKeyboardButton("⬅️ Menu Principale", callback_data='TORNA_MENU_PRINCIPALE')]
        ]
        
        await query.edit_message_text(
            text=(
                "**🍷 PRODOTTI TIPICI LUCANI**\n\n"
                "Scopri le eccellenze enogastronomiche della Basilicata:\n"
                "Prodotti DOP, IGP e tradizioni centenarie"
            ),
            reply_markup=InlineKeyboardMarkup(pulsanti_prodotti),
            parse_mode='Markdown'
        )

    elif data == 'PRODOTTI_FORMAGGI':
        await query.edit_message_text(
            text=(
                "**🧀 FORMAGGI LUCANI DOP**\n\n"
                "🧀 **Caciocavallo Silano DOP**\n"
                "🧀 **Canestrato di Moliterno IGP**\n"
                "🧀 **Pecorino di Filiano DOP**\n"
                "🧀 **Ricotta forte lucana**\n\n"
                "Formaggi prodotti con latte di pascoli montani e tecniche tradizionali.\n\n"
                "🛒 Acquista su https://basilicatago.com"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data='MENU_PRODOTTI_LUCANI')]
            ]),
            parse_mode='Markdown'
        )

    elif data == 'PRODOTTI_SALUMI':
        await query.edit_message_text(
            text=(
                "**🥓 SALUMI E LUCANICA**\n\n"
                "🥓 **Lucanica di Picerno IGP**\n"
                "🥓 **Soppressata lucana**\n"
                "🥓 **Salsiccia al Peperone Crusco**\n"
                "🥓 **Pezzenta** (salame povero)\n\n"
                "Salumi artigianali con carne di maiali allevati allo stato brado.\n\n"
                "🛒 Ordina su https://basilicatago.com"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data='MENU_PRODOTTI_LUCANI')]
            ]),
            parse_mode='Markdown'
        )

    elif data == 'PRODOTTI_VINI':
        await query.edit_message_text(
            text=(
                "**🍷 VINI LUCANI**\n\n"
                "🍷 **Aglianico del Vulture DOC**\n"
                "🍷 **Matera DOC**\n"
                "🍷 **Grottino di Roccanova DOC**\n"
                "🥂 **Malvasia e Moscato**\n\n"
                "Vini pregiati da terreni vulcanici e colline soleggiate.\n\n"
                "🛒 Enoteca su https://basilicatago.com"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data='MENU_PRODOTTI_LUCANI')]
            ]),
            parse_mode='Markdown'
        )

    elif data == 'PRODOTTI_CRUSCHI':
        await query.edit_message_text(
            text=(
                "**🌶️ PEPERONI CRUSCHI IGP**\n\n"
                "Il simbolo della cucina lucana!\n\n"
                "✨ Peperoni di Senise essiccati al sole\n"
                "🔥 Fritti fino a diventare croccanti\n"
                "🍝 Perfetti con pasta e piatti tipici\n"
                "🏅 Presidio Slow Food\n\n"
                "🛒 Acquista su https://basilicatago.com"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data='MENU_PRODOTTI_LUCANI')]
            ]),
            parse_mode='Markdown'
        )

    elif data == 'LINK_PRODOTTI_BASILICATAGO':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "🛒 **Shop Prodotti Lucani**\n\n"
                "Acquista online le eccellenze della Basilicata:\n\n"
                "✅ Spedizione in tutta Italia\n"
                "✅ Produttori selezionati\n"
                "✅ Qualità certificata DOP/IGP\n\n"
                "🔗 **Acquista ora:** https://basilicatago.com"
            ),
            parse_mode='Markdown'
        )

    elif data == 'MENU_SERVIZI_BASILICATAGO':
        pulsanti_servizi = [
            [InlineKeyboardButton("🏠 Strutture Ricettive", callback_data='SERVIZIO_STRUTTURE')],
            [InlineKeyboardButton("📢 Annunci", callback_data='SERVIZIO_ANNUNCI')],
            [InlineKeyboardButton("🛒 Shop Prodotti", callback_data='SERVIZIO_SHOP')],
            [InlineKeyboardButton("🌐 Vai al Portale", callback_data='LINK_PORTALE_BASILICATAGO')],
            [InlineKeyboardButton("⬅️ Menu Principale", callback_data='TORNA_MENU_PRINCIPALE')]
        ]
        
        await query.edit_message_text(
            text=(
                "**📋 SERVIZI BASILICATAGO.COM**\n\n"
                "Il portale completo per turismo e servizi in Basilicata:\n\n"
                "🏨 Prenota strutture ricettive\n"
                "📢 Consulta annunci locali\n"
                "🛒 Acquista prodotti tipici\n"
                "🗺️ Scopri itinerari turistici"
            ),
            reply_markup=InlineKeyboardMarkup(pulsanti_servizi),
            parse_mode='Markdown'
        )

    elif data == 'SERVIZIO_STRUTTURE':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "🏨 **Strutture Ricettive**\n\n"
                "Database completo con:\n"
                "✅ Hotel, B&B, Agriturismi\n"
                "✅ Case vacanza\n"
                "✅ Masserie e dimore storiche\n"
                "✅ Recensioni e contatti diretti\n\n"
                "🔗 https://basilicatago.com"
            ),
            parse_mode='Markdown'
        )

    elif data == 'SERVIZIO_ANNUNCI':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "📢 **Annunci Basilicata**\n\n"
                "Trova e pubblica:\n"
                "🏠 Immobili\n"
                "🚗 Veicoli\n"
                "💼 Servizi locali\n"
                "🎯 Eventi e iniziative\n\n"
                "🔗 https://basilicatago.com"
            ),
            parse_mode='Markdown'
        )

    elif data == 'SERVIZIO_SHOP':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "🛒 **Shop Prodotti Lucani**\n\n"
                "Acquista online:\n"
                "🧀 Formaggi DOP/IGP\n"
                "🥓 Salumi artigianali\n"
                "🍷 Vini pregiati\n"
                "🌶️ Peperoni Cruschi\n\n"
                "Spedizione in tutta Italia!\n\n"
                "🔗 https://basilicatago.com"
            ),
            parse_mode='Markdown'
        )

    elif data == 'LINK_PORTALE_BASILICATAGO':
        await query.answer("Apertura in corso...", show_alert=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "🌐 **BasilicataGo - Portale Turistico**\n\n"
                "Il riferimento per scoprire e vivere la Basilicata:\n\n"
                "🏛️ Destinazioni e attrazioni\n"
                "🏨 Prenotazioni strutture\n"
                "🛒 Shop prodotti locali\n"
                "📢 Annunci e servizi\n"
                "📰 News e eventi\n\n"
                "🔗 **Visita ora:** https://basilicatago.com"
            ),
            parse_mode='Markdown'
        )


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def main() -> None:
    """Avvia il bot con pubblicazioni automatiche."""
    global pubblicazione_task
    
    application = Application.builder().token(TOKEN).build()
    
    # Registra i comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pubblica", pubblica))
    application.add_handler(CommandHandler("pubblica_bot", pubblica_bot))
    application.add_handler(CommandHandler("test_canale", test_canale))
    application.add_handler(CommandHandler("programma", programma))  # 🆕
    application.add_handler(CommandHandler("lista_programmati", lista_programmati))  # 🆕
    application.add_handler(CommandHandler("cancella_programmato", cancella_programmato))  # 🆕
    application.add_handler(CommandHandler("imposta_orario", imposta_orario))
    application.add_handler(CommandHandler("stato_bot", stato_bot))
    application.add_handler(CommandHandler("verifica_permessi", verifica_permessi))
    application.add_handler(CommandHandler("help", help_admin))
    
    # Handler per i pulsanti inline
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Handler per il pulsante "Scopri la Basilicata"
    application.add_handler(MessageHandler(
        filters.Regex("^🏛️ Scopri la Basilicata$"), 
        handle_menu_button
    ))
    
    # Handler per cancellare altri messaggi
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏛️ Scopri la Basilicata$"), 
        handle_other_messages
    ))
    
    # ✅ AVVIA PUBBLICAZIONE AUTOMATICA (SENZA JOB_QUEUE)
    loop = asyncio.get_event_loop()
    pubblicazione_task = loop.create_task(loop_pubblicazione_quotidiana(application))
    
    logger.info("✅ Sistema di pubblicazione automatica avviato")
    logger.info(f"📅 Orario predefinito: {orario_pubblicazione['ore']:02d}:{orario_pubblicazione['minuti']:02d}")
    logger.info("🆕 Sistema messaggi programmati attivo")
    logger.info("🚀 Bot @basilicatagobot avviato e in ascolto...")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except KeyboardInterrupt:
        if pubblicazione_task:
            pubblicazione_task.cancel()
        # Cancella tutti i messaggi programmati
        for info in messaggi_programmati.values():
            if not info['task'].done():
                info['task'].cancel()
        logger.info("Bot fermato dall'utente")


if __name__ == '__main__':
    main()
