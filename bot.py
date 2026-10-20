import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

DB_NAME = "routine.db"


def init_db():
  """Initializes SQLite DB and populates default tasks if empty."""
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            done INTEGER DEFAULT 0
        )
    """)
  conn.commit()

  # Insert default tasks if database is brand new
  cursor.execute("SELECT COUNT(*) FROM tasks")
  if cursor.fetchone()[0] == 0:
    defaults = [
        "🌅 Wake up & Hydrate",
        "💻 Core Coding / Project Work",
        "📚 Study / Skill Building",
        "🏋️ Exercise / Workout",
        "🌙 Plan Tomorrow's Tasks",
    ]
    for task in defaults:
      cursor.execute("INSERT INTO tasks (name, done) VALUES (?, 0)", (task,))
    conn.commit()
  conn.close()


def get_tasks():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, done FROM tasks")
  rows = cursor.fetchall()
  conn.close()
  return rows


def toggle_task(task_id):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE tasks SET done = CASE WHEN done = 1 THEN 0 ELSE 1 END WHERE id ="
      " ?",
      (task_id,),
  )
  conn.commit()
  conn.close()


def reset_tasks():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("UPDATE tasks SET done = 0")
  conn.commit()
  conn.close()


def add_task(name):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("INSERT INTO tasks (name, done) VALUES (?, 0)", (name,))
  conn.commit()
  conn.close()


def get_keyboard():
  tasks = get_tasks()
  keyboard = []
  for t_id, name, done in tasks:
    status = "✅" if done else "⬜"
    keyboard.append(
        [InlineKeyboardButton(f"{status} {name}", callback_data=f"toggle_{t_id}")]
    )

  keyboard.append([
      InlineKeyboardButton("🔄 Reset Day", callback_data="action_reset"),
      InlineKeyboardButton("📊 Summary", callback_data="action_summary"),
  ])
  return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  tasks = get_tasks()
  completed = sum(1 for _, _, done in tasks if done)
  total = len(tasks)

  text = (
      f"📌 *DAILY ROUTINE & TASK HUB*\nProgress: {completed}/{total}"
      " completed\n\nTap a task to mark it done:"
  )

  await context.bot.send_message(
      chat_id=update.effective_chat.id,
      text=text,
      reply_markup=get_keyboard(),
      parse_mode="Markdown",
  )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Allows adding new tasks via '/add Read 20 pages'."""
  task_name = " ".join(context.args)
  if not task_name:
    await update.message.reply_text("Usage: `/add Task Name`", parse_mode="Markdown")
    return

  add_task(task_name)
  await update.message.reply_text(f"➕ Added: *{task_name}*", parse_mode="Markdown")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  data = query.data

  if data.startswith("toggle_"):
    t_id = int(data.split("_")[1])
    toggle_task(t_id)
  elif data == "action_reset":
    reset_tasks()
  elif data == "action_summary":
    tasks = get_tasks()
    done_list = [f"• {name}" for _, name, d in tasks if d]
    pending_list = [f"• {name}" for _, name, d in tasks if not d]

    msg = (
        "📊 *Daily Summary*\n\n"
        f"*Completed ({len(done_list)}):*\n"
        + ("\n".join(done_list) if done_list else "None")
        + f"\n\n*Pending ({len(pending_list)}):*\n"
        + ("\n".join(pending_list) if pending_list else "All done! 🎉")
    )
    await query.message.reply_text(msg, parse_mode="Markdown")
    return

  tasks = get_tasks()
  completed = sum(1 for _, _, done in tasks if done)
  total = len(tasks)
  text = (
      f"📌 *DAILY ROUTINE & TASK HUB*\nProgress: {completed}/{total}"
      " completed\n\nTap a task to mark it done:"
  )

  try:
    await query.edit_message_text(
        text=text, reply_markup=get_keyboard(), parse_mode="Markdown"
    )
  except Exception:
    pass


if __name__ == "__main__":
  init_db()

  # Replace with your actual token from BotFather
  TOKEN = "8273741743:AAGfnonjp3LQm2p4-VXCBY_5aa_5HqRB87w"

  app = ApplicationBuilder().token(TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("menu", start))
  app.add_handler(CommandHandler("add", add_command))
  app.add_handler(CallbackQueryHandler(button_handler))

  print("🚀 Bot is live with persistent SQLite storage...")
  app.run_polling()