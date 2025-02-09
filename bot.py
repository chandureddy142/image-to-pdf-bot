import os
import logging
import asyncio
import img2pdf
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext
)

# Load bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Set up logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary storage for images
IMG_DIR = "images"
os.makedirs(IMG_DIR, exist_ok=True)

# Dictionary to store user images
user_images = {}

# Declare the private channel ID or username
CHANNEL_ID = "-1002295027859"  # Replace with your actual channel ID or @username

# Command to start the bot and send a welcome message
async def start(update: Update, context: CallbackContext):
    """Send a welcome message."""
    await update.message.reply_text("📷 Send me images, and I'll upload them to a private channel and convert them into a PDF! Use /convert when you're ready.")

# Handle incoming images
async def handle_image(update: Update, context: CallbackContext):
    """Handle incoming images, upload them to the private channel, and store the image file."""
    chat_id = update.message.chat_id
    photo = update.message.photo[-1]  # Get the highest resolution image
    file = await photo.get_file()

    # Save file path for the user
    file_path = os.path.join(IMG_DIR, f"{chat_id}_{photo.file_id}.jpg")
    
    # Download and save the image
    await file.download_to_drive(file_path)
    
    # Send the image to the private channel
    await context.bot.send_photo(CHANNEL_ID, photo=file.file_id)

    # Add the file path to the user's list of images
    if chat_id not in user_images:
        user_images[chat_id] = []
    user_images[chat_id].append(file_path)

    await update.message.reply_text("✅ Image uploaded to the private channel! Send more images or use /convert to generate a PDF.")

# Convert images to a PDF and send it to the user
async def convert_to_pdf(update: Update, context: CallbackContext):
    """Convert images to a single PDF and send the PDF to the user."""
    chat_id = update.message.chat_id

    if chat_id not in user_images or not user_images[chat_id]:
        await update.message.reply_text("⚠️ No images found! Please send some images first.")
        return

    pdf_path = os.path.join(IMG_DIR, f"{chat_id}.pdf")

    try:
        # Convert images to PDF using img2pdf
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(img2pdf.convert(user_images[chat_id]))

        # Send the PDF to the user
        await update.message.reply_document(document=open(pdf_path, "rb"), filename="converted.pdf")

        # Cleanup: remove images and the PDF after sending
        for img in user_images[chat_id]:
            os.remove(img)
        os.remove(pdf_path)

        # Clear the list of images for the user
        del user_images[chat_id]

        await update.message.reply_text("✅ PDF generated and sent successfully!")

    except Exception as e:
        logger.error(f"Error converting PDF: {e}")
        await update.message.reply_text("❌ An error occurred while generating the PDF.")

# Main function to start the bot
async def main():
    """Start the bot."""
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(CommandHandler("convert", convert_to_pdf))

    logger.info("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
