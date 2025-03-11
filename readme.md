# Trilium Telegram Bot

A powerful Telegram bot for seamless interaction with [Trilium Notes](https://github.com/zadam/trilium), combining features from [TGTriliumBot](https://github.com/domenicop-1991/TGTriliumBot) and [trilium-bot](https://github.com/Nriver/trilium-bot).

## ✨ Features

- 📝 **Note Creation** - Create new notes directly from Telegram
- 📎 **Attachment Upload** - Easily upload files to your Trilium notes
- ✅ **TODO Management** - View, check, add, update, and delete TODO items
- 🔄 **Automated Tasks** - Move yesterday's unfinished TODOs to today's note
- 🎮 **Interactive Interface** - Inline buttons for intuitive navigation

## 🚀 Quick Start

### Prerequisites

- A running Trilium Notes server
- Docker and Docker Compose
- A Telegram bot token (get one from [BotFather](https://t.me/botfather))

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ktibr0/Trilium_telegram_bot
   cd Trilium_telegram_bot
   ```

2. Configure environment variables:
   ```bash
   cp example.env .env
   ```
   
   Edit `.env` with your details:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TRILIUM_ETAPI_TOKEN=your_trilium_token
   TRILIUM_API_URL=https://URL_for_Your_Trilium_server
   admin_list=your_telegram_id
   ```

3. Build and run the Docker container:
   ```bash
   docker compose up --build -d
   ```

   For detailed logs:
   ```bash
   docker compose up --build -d && docker compose logs -f
   ```

## 📱 Usage

1. Start the bot by sending `/start` in your Telegram chat
2. Use the interactive menu to access various features:

### Creating Notes
Select "Create Note" and follow the prompts to add a title and content.

### Managing Attachments
First, create a note titled "FromTelegram" in your Trilium.
Then select "Create Attachment" in the bot, provide a name, and upload your file.

> **Note:** Attachments remain for 30 days unless converted to notes. Access them by going to the note, clicking the 3 dots menu, and selecting "Note attachments".

### Quick Notes
Simply send text messages to the bot to save them as subnotes to today's note.

### TODO Management
- Select "TODO List" to view today's TODOs
- Tap items to check/uncheck them
- Use the function buttons to add, update, or delete TODOs

### Automated Tasks
The bot automatically moves yesterday's unfinished TODOs to today's note. Customize the schedule in `config.json`.

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Open a [Pull Request](https://github.com/ktibr0/Trilium_telegram_bot/pulls)
- Report issues through the [Issue tracker](https://github.com/ktibr0/Trilium_telegram_bot/issues)

## 🙏 Acknowledgements

This project builds upon the work done in:
- [TGTriliumBot](https://github.com/domenicop-1991/TGTriliumBot)
- [trilium-bot](https://github.com/Nriver/trilium-bot)
