import asyncio
import json
import logging
import os
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from telegram.constants import BotCommandScopeType
from telegram import BotCommandScope

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from trilium_py.client import ETAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve variables from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRILIUM_ETAPI_TOKEN = os.getenv("TRILIUM_ETAPI_TOKEN")
TRILIUM_API_URL = os.getenv("TRILIUM_API_URL")
ADMIN_LIST = [int(id_str) for id_str in os.getenv("admin_list", "").split(",") if id_str.strip()]

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory variables
user_data = {}  # Stores temporary data for conversations
config_file = 'config.json'
config = {}
start_time = datetime.now()


@dataclass
class TODO:
    index: int = None
    description: str = None


# ---- Configuration functions ----

def load_config():
    """Load configuration from config.json file"""
    global config
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.loads(f.read())
    
    # Default configs
    default_config = {
        'quick_add': True,
        'single_note': False,
        'move_yesterday_unfinished_todo': True,
        'move_todo_time': '00:05',
    }
    
    for key in default_config:
        if key not in config:
            config[key] = default_config[key]


def save_config():
    """Save configuration to config.json file"""
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(config, ensure_ascii=False, indent=4))


# ---- Authorization decorator ----

def restricted(func):
    """Restrict access to bot commands"""
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_LIST:
            logger.warning(f"Unauthorized access denied for {user_id}")
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


# ---- Menu building functions ----

def build_main_menu():
    """Build the main menu inline keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("TODO List", callback_data=json.dumps({"type": "todo_list"})),
            InlineKeyboardButton("Toggle Quick Add", callback_data=json.dumps({"type": "toggle_quick_add"}))
        ],
        [
            InlineKeyboardButton("Create Note", callback_data=json.dumps({"type": "create_note"})),
            InlineKeyboardButton("Create Attachment", callback_data=json.dumps({"type": "create_attachment"}))
        ],
        [
            InlineKeyboardButton("Status", callback_data=json.dumps({"type": "status"})),
            InlineKeyboardButton("ID", callback_data=json.dumps({"type": "id"})),
            InlineKeyboardButton("Restart", callback_data=json.dumps({"type": "restart"}))
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_todo_list_markup(todo_list: List[Tuple[bool, str]], callback_type='todo_toggle'):
    """Build inline keyboard for todo list"""
    keyboard = []
    for i, (status, todo) in enumerate(todo_list):
        text = '✅ ' + todo if status else '🟩 ' + todo
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=json.dumps({
                    'type': callback_type,
                    'index': i,
                    'status': status
                })
            )
        ])
    
    # Add buttons for adding, updating, and deleting todos
    keyboard.append([
        InlineKeyboardButton("Add", callback_data=json.dumps({'type': 'todo_add'})),
        InlineKeyboardButton("Update", callback_data=json.dumps({'type': 'todo_update'})),
        InlineKeyboardButton("Delete", callback_data=json.dumps({'type': 'todo_delete'}))
    ])
    
    # Add back button
    keyboard.append([
        InlineKeyboardButton("Back to Menu", callback_data=json.dumps({'type': 'back_to_menu'}))
    ])
    
    return InlineKeyboardMarkup(keyboard)


def build_confirm_markup(callback_type):
    """Build confirmation dialog markup"""
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=json.dumps({'type': callback_type, 'confirm': True}))],
        [InlineKeyboardButton("No", callback_data=json.dumps({'type': callback_type, 'confirm': False}))]
    ]
    return InlineKeyboardMarkup(keyboard)


# ---- Command handlers ----

@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    chat_id = update.effective_chat.id
    
    # Set up bot commands - без использования scope
    await context.bot.set_my_commands(
        commands=[
            ("start", "Show main menu"),
            ("move", "Move yesterday's unfinished todos to today")
        ]
    )
    
    await update.message.reply_text(
        "Welcome to Trilium Bot! Please select an option:",
        reply_markup=build_main_menu()
    )

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send user their Telegram ID"""
    await update.message.reply_text(f"Your Telegram ID is: {update.effective_user.id}")


@restricted
async def move_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Move yesterday's unfinished todos to today"""
    await move_todo_job()
    await update.message.reply_text("Yesterday's unfinished todos have been moved to today.")


# ---- Callback query handler ----

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    data = json.loads(query.data)
    callback_type = data['type']
    
    # Main menu options
    if callback_type == "back_to_menu":
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Main Menu:",
            reply_markup=build_main_menu()
        )
    
    elif callback_type == "todo_list":
        todo_list = trilium_client.get_todo()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Current TODO List:",
            reply_markup=build_todo_list_markup(todo_list)
        )
    
    elif callback_type == "toggle_quick_add":
        config['quick_add'] = not config['quick_add']
        save_config()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Quick Add mode is now {'ON' if config['quick_add'] else 'OFF'}",
            reply_markup=build_main_menu()
        )
    
    elif callback_type == "create_note":
        user_data[chat_id] = {"action": "create_note"}
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Please enter the title for your note:"
        )
    
    elif callback_type == "create_attachment":
        user_data[chat_id] = {"action": "create_attachment"}
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Please enter a name for your attachment:"
        )
    
    elif callback_type == "status":
        uptime = str(datetime.now() - start_time).split('.')[0]
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Bot has been running for {uptime}",
            reply_markup=build_main_menu()
        )
    
    elif callback_type == "id":
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Your Telegram ID is: {update.effective_user.id}",
            reply_markup=build_main_menu()
        )
    
    elif callback_type == "restart":
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Bot is restarting..."
        )
        # Schedule restart after message is sent
        context.job_queue.run_once(restart_bot, 1)
    
    # TODO list operations
    elif callback_type == "todo_toggle":
        index = data['index']
        status = data['status']
        trilium_client.todo_check(index, check=not status)
        todo_list = trilium_client.get_todo()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Current TODO List:",
            reply_markup=build_todo_list_markup(todo_list)
        )
    
    elif callback_type == "todo_add":
        user_data[chat_id] = {"action": "add_todo"}
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Please enter the description for your new TODO item:"
        )
    
    elif callback_type == "todo_update":
        todo_list = trilium_client.get_todo()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Select a TODO item to update:",
            reply_markup=build_todo_list_markup(todo_list, "todo_update_select")
        )
    
    elif callback_type == "todo_update_select":
        index = data['index']
        user_data[chat_id] = {"action": "update_todo", "index": index}
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Please enter the new description for this TODO item:"
        )
    
    elif callback_type == "todo_delete":
        todo_list = trilium_client.get_todo()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Select a TODO item to delete:",
            reply_markup=build_todo_list_markup(todo_list, "todo_delete_select")
        )
    
    elif callback_type == "todo_delete_select":
        index = data['index']
        todo_description = trilium_client.get_todo()[index][1]
        user_data[chat_id] = {"action": "delete_todo", "index": index}
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Are you sure you want to delete '{todo_description}'?",
            reply_markup=build_confirm_markup("todo_delete_confirm")
        )
    
    elif callback_type == "todo_delete_confirm":
        confirm = data['confirm']
        if confirm:
            index = user_data[chat_id]["index"]
            trilium_client.delete_todo(index)
            todo_list = trilium_client.get_todo()
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="TODO item deleted. Current TODO List:",
                reply_markup=build_todo_list_markup(todo_list)
            )
        else:
            todo_list = trilium_client.get_todo()
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="Deletion cancelled. Current TODO List:",
                reply_markup=build_todo_list_markup(todo_list)
            )


# ---- Message handlers ----

@restricted
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    chat_id = update.effective_chat.id
    text = update.message.text
    
    # If no ongoing action, handle as a quick add if enabled
    if chat_id not in user_data:
        if config['quick_add']:
            day_note = trilium_client.inbox(datetime.now().strftime("%Y-%m-%d"))
            trilium_client.create_note(
                parentNoteId=day_note['noteId'],
                title="TG message",
                type="text",
                content=text,
            )
            await update.message.reply_text(
                "Message added to Trilium",
                reply_markup=build_main_menu()
            )
        else:
            await update.message.reply_text(
                "Please use the menu to select an action:",
                reply_markup=build_main_menu()
            )
        return
    
    action_data = user_data[chat_id]
    action = action_data["action"]
    
    # Handle different actions
    if action == "create_note":
        if "title" not in action_data:
            # First step: save title and ask for content
            user_data[chat_id]["title"] = text
            await update.message.reply_text("Enter the content for your note:")
        else:
            # Second step: create the note
            title = user_data[chat_id]["title"]
            content = text
            
            try:
                note = trilium_client.create_note(
                    parentNoteId="root", 
                    title=title, 
                    content=content, 
                    type="text"
                )
                note_id = note['note']['noteId']
                
                await update.message.reply_text(
                    f"Note created successfully!\nNote ID: {note_id}",
                    reply_markup=build_main_menu()
                )
            except Exception as e:
                logger.error(f"Error creating note: {e}")
                await update.message.reply_text(
                    "Error creating note!",
                    reply_markup=build_main_menu()
                )
            finally:
                del user_data[chat_id]
    
    elif action == "create_attachment":
        if "title" not in action_data:
            # First step: save title and ask for file
            user_data[chat_id]["title"] = text
            await update.message.reply_text("Please send the file for attachment:")
        else:
            # Expecting a file, not text
            await update.message.reply_text("Please send a file, not text!")
    
    elif action == "add_todo":
        # Add a new TODO item
        todo_description = text.strip()
        trilium_client.add_todo(todo_description)
        todo_list = trilium_client.get_todo()
        
        await update.message.reply_text(
            "TODO item added. Current TODO List:",
            reply_markup=build_todo_list_markup(todo_list)
        )
        del user_data[chat_id]
    
    elif action == "update_todo":
        # Update an existing TODO item
        index = action_data["index"]
        new_description = text.strip()
        trilium_client.update_todo(index, new_description)
        todo_list = trilium_client.get_todo()
        
        await update.message.reply_text(
            "TODO item updated. Current TODO List:",
            reply_markup=build_todo_list_markup(todo_list)
        )
        del user_data[chat_id]
    
    elif action == "delete_todo":
        # This shouldn't happen as delete is handled via callbacks
        await update.message.reply_text(
            "Please use the menu to manage TODO items:",
            reply_markup=build_main_menu()
        )
        del user_data[chat_id]


@restricted
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document/file uploads"""
    chat_id = update.effective_chat.id
    document = update.message.document
    
    if chat_id not in user_data or user_data[chat_id]["action"] != "create_attachment":
        await update.message.reply_text(
            "Please use the menu to select an action first:",
            reply_markup=build_main_menu()
        )
        return
    
    title = user_data[chat_id]["title"]
    
    # Download the file
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    
    # Create temporary file path
    temp_file_path = f"/tmp/{document.file_name}"
    
    try:
        # Save file locally
        with open(temp_file_path, "wb") as f:
            f.write(file_content)
        
        # Search for FromTelegram note
        results = trilium_client.search_note(search="FromTelegram")
        if results['results']:
            parent_id = results['results'][0]['noteId']
            
            # Create attachment
            attachment = trilium_client.create_attachment(
                ownerId=parent_id,
                file_path=temp_file_path
            )
            attachment_id = attachment['note']['noteId']
            
            # Update the content of the note
            note_content = trilium_client.get_note_content(parent_id)
            attachment_url = f"/api/attachments/{attachment_id}"
            updated_content = f"{note_content}\n![{document.file_name}]({attachment_url})"
            trilium_client.update_note_content(parent_id, updated_content)
            
            await update.message.reply_text(
                f"Attachment uploaded successfully!\nAttachment ID: {attachment_id}",
                reply_markup=build_main_menu()
            )
        else:
            await update.message.reply_text(
                "The 'FromTelegram' note was not found.",
                reply_markup=build_main_menu()
            )
    except Exception as e:
        logger.error(f"Error uploading attachment: {e}")
        await update.message.reply_text(
            "Error uploading attachment!",
            reply_markup=build_main_menu()
        )
    finally:
        # Remove temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        del user_data[chat_id]


# ---- Scheduler and task functions ----

async def move_todo_job():
    """Move yesterday's unfinished todos to today"""
    logger.info("Moving yesterday's unfinished todos to today")
    trilium_client.move_yesterday_unfinished_todo_to_today()


async def restart_bot(context: ContextTypes.DEFAULT_TYPE):
    """Restart the bot"""
    logger.info("Restarting bot...")
    os.execv(sys.executable, ['python'] + sys.argv)


async def schedule_daily_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Schedule daily tasks based on config"""
    if config['move_yesterday_unfinished_todo']:
        # Parse time from config
        move_time = config['move_todo_time']
        hours, minutes = map(int, move_time.split(':'))
        
        # Schedule the job
        now = datetime.now()
        target_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        # If the time has already passed today, schedule for tomorrow
        if now > target_time:
            target_time = target_time.replace(day=now.day + 1)
        
        # Calculate seconds until target time
        seconds_until_target = (target_time - now).total_seconds()
        
        # Schedule the job
        context.job_queue.run_once(
            lambda _: asyncio.create_task(move_todo_job()),
            seconds_until_target
        )
        
        # Also schedule it to run daily after that
        context.job_queue.run_daily(
            lambda _: asyncio.create_task(move_todo_job()),
            target_time.time()
        )


# ---- Main function ----

def main():
    """Start the bot"""
    global trilium_client
    
    # Load configuration
    load_config()
    save_config()
    
    # Initialize Trilium client
    trilium_client = ETAPI(TRILIUM_API_URL, TRILIUM_ETAPI_TOKEN)
    
    # Create application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("move", move_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    
    # Schedule daily tasks
    application.job_queue.run_once(schedule_daily_tasks, 1)
    
    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()