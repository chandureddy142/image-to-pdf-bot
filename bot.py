import os
import logging
import asyncio
import img2pdf
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from flask import Flask

# Load bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Set up logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary storage for images
IMG_DIR = "images"
os.makedirs(IMG_DIR, exist_ok=True)

# Dictionary to store user images
user_images = {}

# Flask app to keep Render service alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

async def start(update: Update, context: CallbackContext):
    """Send a welcome message."""
    await update.message.reply_text("📷 Send me images, and I'll convert them into a PDF! Use /convert when you're ready.")

async def handle_image(update: Update, context: CallbackContext):
    """Handle incoming images."""
    chat_id = update.message.chat_id
    photo = update.message.photo[-1]  # Get the highest resolution image
    file = await photo.get_file()

    # File path
    file_path = os.path.join(IMG_DIR, f"{chat_id}_{photo.file_id}.jpg")

    # Download the image
    await file.download_to_drive(file_path)

    # Store file path in user's list
    if chat_id not in user_images:
        user_images[chat_id] = []
    user_images[chat_id].append(file_path)

    await update.message.reply_text("✅ Image saved! Send more or use /convert to generate a PDF.")

async def convert_to_pdf(update: Update, context: CallbackContext):
    """Convert images to a single PDF."""
    chat_id = update.message.chat_id

    if chat_id not in user_images or not user_images[chat_id]:
        await update.message.reply_text("⚠️ No images found! Please send some images first.")
        return

    pdf_path = os.path.join(IMG_DIR, f"{chat_id}.pdf")

    try:
        # Convert images to PDF
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(img2pdf.convert(user_images[chat_id]))

        # Send PDF to user
        await update.message.reply_document(document=open(pdf_path, "rb"), filename="converted.pdf")

        # Cleanup
        for img in user_images[chat_id]:
            os.remove(img)
        os.remove(pdf_path)
        del user_images[chat_id]

        await update.message.reply_text("✅ PDF generated and sent successfully!")

    except Exception as e:
        logger.error(f"Error converting PDF: {e}")
        await update.message.reply_text("❌ An error occurred while generating the PDF.")

async def main():
    """Start the bot."""
    bot_app = Application.builder().token(TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    bot_app.add_handler(CommandHandler("convert", convert_to_pdf))

    logger.info("Bot is running...")

    # Start bot in a separate task
    asyncio.create_task(bot_app.run_polling())

if __name__ == "__main__":
    import threading

    # Start Telegram bot in a separate thread
    bot_thread = threading.Thread(target=asyncio.run, args=(main(),))
    bot_thread.start()

    # Start Flask server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
