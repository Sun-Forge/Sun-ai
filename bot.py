"""
SUN AI - Telegram Bot
Bot chính với menu ReplyKeyboardMarkup
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict

from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton,
    ChatAction
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from telegram.error import TelegramError
from dotenv import load_dotenv

from database import Database
from github_manager import GitHubManager

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Khởi tạo database
db = Database()

# Khởi tạo GitHub Manager
try:
    github_manager = GitHubManager()
except Exception as e:
    logger.warning(f"GitHub Manager initialization failed: {e}")
    github_manager = None

# Load models
with open("models.json", "r", encoding="utf-8") as f:
    MODELS_DATA = json.load(f)
    MODELS = {m["id"]: m for m in MODELS_DATA["models"]}

# Conversation states
(
    MENU_STATE,
    CREATE_AI_SELECT_MODEL,
    CHOOSE_MODEL,
    CONFIRM_CREATE,
    DELETE_AI_CONFIRM,
    SETTINGS_MENU
) = range(6)

# ============ Helper Functions ============

def get_main_menu_keyboard():
    """Tạo main menu keyboard"""
    keyboard = [
        ["🤖 Tạo AI", "🧠 Chọn Model"],
        ["📊 AI Hiện Tại", "🔑 API Của Tôi"],
        ["📜 Danh Sách AI", "📈 Thống Kê"],
        ["⚡ Trạng Thái VPS", "🔄 Làm Mới"],
        ["❌ Xóa AI", "⚙️ Cài Đặt"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_model_selection_keyboard():
    """Tạo model selection keyboard"""
    keyboard = []
    for model_id, model_info in MODELS.items():
        keyboard.append([f"🤖 {model_info['name']}"])
    
    keyboard.append(["⬅️ Quay Lại"])
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def format_node_info(node: Dict) -> str:
    """Format thông tin node để hiển thị"""
    status_icon = "🟢" if node["status"] == "online" else "🔴"
    
    text = f"""
{status_icon} *Trạng Thái AI*
- Chat ID: `{node['chat_id']}`
- Model: `{node['model']}`
- Trạng thái: {node['status'].upper()}
- Requests: {node['requests']}
- Tokens: {node['tokens']:,}
- Last Seen: {node['last_seen']}
- Created: {node['created_at']}
"""
    return text

# ============ Start Command ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho /start command"""
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Thêm user vào database
        db.add_user(
            chat_id=chat_id,
            username=user.username or "Unknown",
            first_name=user.first_name or "Unknown"
        )
        
        # Gửi welcome message
        welcome_text = f"""
Xin chào {user.first_name}! 👋

Đây là SUN AI Bot - Hệ thống AI được chạy trên GitHub Actions.

Chọn tác vụ từ menu dưới đây:
"""
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_menu_keyboard()
        )
        
        logger.info(f"User {chat_id} started the bot")
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")

# ============ Main Menu Handlers ============

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler cho main menu"""
    try:
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        # Cập nhật user activity
        db.update_user_activity(chat_id)
        
        if message_text == "🤖 Tạo AI":
            return await create_ai(update, context)
        elif message_text == "🧠 Chọn Model":
            return await choose_model(update, context)
        elif message_text == "📊 AI Hiện Tại":
            return await show_current_ai(update, context)
        elif message_text == "🔑 API Của Tôi":
            return await show_api_key(update, context)
        elif message_text == "📜 Danh Sách AI":
            return await list_all_ai(update, context)
        elif message_text == "📈 Thống Kê":
            return await show_stats(update, context)
        elif message_text == "⚡ Trạng Thái VPS":
            return await show_vps_status(update, context)
        elif message_text == "🔄 Làm Mới":
            return await refresh(update, context)
        elif message_text == "❌ Xóa AI":
            return await delete_ai(update, context)
        elif message_text == "⚙️ Cài Đặt":
            return await settings(update, context)
        else:
            await update.message.reply_text(
                "❌ Lệnh không được nhận diện. Vui lòng chọn từ menu.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in handle_menu: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

# ============ Create AI ============

async def create_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bước 1: Chọn model khi tạo AI"""
    try:
        chat_id = update.effective_chat.id
        
        # Kiểm tra nếu user đã có AI đang chạy
        api_key_info = db.get_api_key_by_chat_id(chat_id)
        if api_key_info and api_key_info["active"]:
            node = db.get_node(chat_id)
            if node and node["status"] == "online":
                await update.message.reply_text(
                    f"⚠️ Bạn đã có một AI đang chạy.\n\n"
                    f"Model: {node['model']}\n"
                    f"Hãy xóa AI hiện tại trước khi tạo AI mới.",
                    reply_markup=get_main_menu_keyboard()
                )
                return MENU_STATE
        
        await update.message.reply_text(
            "🤖 Chọn model cho AI của bạn:\n\n"
            "Các model hỗ trợ:",
            reply_markup=get_model_selection_keyboard()
        )
        
        context.user_data['creating_ai'] = True
        return CREATE_AI_SELECT_MODEL
    
    except Exception as e:
        logger.error(f"Error in create_ai: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def create_ai_select_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bước 2: Xác nhận model được chọn"""
    try:
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        if message_text == "⬅️ Quay Lại":
            await update.message.reply_text(
                "Đã hủy tạo AI.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
        
        # Tìm model từ message
        selected_model = None
        for model_id, model_info in MODELS.items():
            if model_info['name'] in message_text:
                selected_model = model_id
                selected_model_info = model_info
                break
        
        if not selected_model:
            await update.message.reply_text(
                "❌ Model không hợp lệ. Vui lòng chọn từ danh sách.",
                reply_markup=get_model_selection_keyboard()
            )
            return CREATE_AI_SELECT_MODEL
        
        # Lưu model được chọn
        context.user_data['selected_model'] = selected_model
        
        # Hiển thị thông tin model
        model_info_text = f"""
✅ *Model Được Chọn*

📌 Tên: {selected_model_info['name']}
📝 Mô tả: {selected_model_info['description']}
💾 Dung lượng: {selected_model_info['size_gb']}GB
💻 VRAM cần: {selected_model_info['vram_mb']}MB

Nhấn 'Xác Nhận' để tiếp tục, hoặc 'Hủy' để quay lại.
"""
        
        keyboard = [
            ["✅ Xác Nhận", "❌ Hủy"]
        ]
        
        await update.message.reply_text(
            model_info_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
        return CONFIRM_CREATE
    
    except Exception as e:
        logger.error(f"Error in create_ai_select_model: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return CREATE_AI_SELECT_MODEL

async def confirm_create_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bước 3: Xác nhận và trigger workflow"""
    try:
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        if message_text == "❌ Hủy":
            await update.message.reply_text(
                "Đã hủy tạo AI.",
                reply_markup=get_main_menu_keyboard()
            )
            context.user_data['creating_ai'] = False
            return MENU_STATE
        
        selected_model = context.user_data.get('selected_model')
        if not selected_model:
            await update.message.reply_text(
                "❌ Lỗi: Model không được chọn.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
        
        # Gửi typing notification
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Tạo API Key
        api_key = GitHubManager.generate_api_key(chat_id)
        
        # Lưu API Key vào database
        db.add_api_key(api_key, chat_id, selected_model)
        
        # Trigger GitHub workflow
        if github_manager:
            workflow_result = github_manager.trigger_workflow(chat_id, selected_model)
            if workflow_result:
                run_id = workflow_result["run_id"]
                db.update_api_key_run_id(api_key, run_id)
                
                success_text = f"""
✅ *AI Được Tạo Thành Công!*

🔑 API Key: `{api_key}`
🤖 Model: {MODELS[selected_model]['name']}
📌 Chat ID: `{chat_id}`
⏱️ Thời gian tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔗 Workflow: {workflow_result['html_url']}

⏳ Vui lòng chờ... GitHub Actions đang cài đặt model.
Quá trình này có thể mất 5-10 phút.

📊 Bạn có thể kiểm tra trạng thái trong menu "⚡ Trạng Thái VPS"
"""
                
                await update.message.reply_text(
                    success_text,
                    parse_mode="Markdown",
                    reply_markup=get_main_menu_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Lỗi: Không thể trigger GitHub workflow.",
                    reply_markup=get_main_menu_keyboard()
                )
        else:
            success_text = f"""
✅ *AI Được Tạo Thành Công!*

🔑 API Key: `{api_key}`
🤖 Model: {MODELS[selected_model]['name']}
📌 Chat ID: `{chat_id}`
"""
            
            await update.message.reply_text(
                success_text,
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard()
            )
        
        context.user_data['creating_ai'] = False
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in confirm_create_ai: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

# ============ Other Menu Handlers ============

async def choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem danh sách model hỗ trợ"""
    try:
        model_list = "🧠 *Danh Sách Model Hỗ Trợ*\n\n"
        
        for idx, (model_id, model_info) in enumerate(MODELS.items(), 1):
            model_list += f"""{idx}. {model_info['name']}
   • Mô tả: {model_info['description']}
   • Dung lượng: {model_info['size_gb']}GB
   • VRAM: {model_info['vram_mb']}MB

"""
        
        await update.message.reply_text(
            model_list,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in choose_model: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def show_current_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem AI hiện tại"""
    try:
        chat_id = update.effective_chat.id
        
        node = db.get_node(chat_id)
        if not node:
            await update.message.reply_text(
                "❌ Bạn chưa có AI nào đang chạy.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
        
        info_text = format_node_info(node)
        
        await update.message.reply_text(
            info_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in show_current_ai: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def show_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem API Key của tôi"""
    try:
        chat_id = update.effective_chat.id
        
        api_key_info = db.get_api_key_by_chat_id(chat_id)
        if not api_key_info:
            await update.message.reply_text(
                "❌ Bạn chưa có API Key nào.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
        
        key_text = f"""
🔑 *API Key Của Tôi*

API Key: `{api_key_info['api_key']}`
Model: {api_key_info['model_id']}
Tạo lúc: {api_key_info['created_at']}
Trạng thái: {'✅ Hoạt động' if api_key_info['active'] else '❌ Vô hiệu'}

⚠️ Giữ kín API Key này!
Đừng chia sẻ với bất kỳ ai.
"""
        
        await update.message.reply_text(
            key_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in show_api_key: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def list_all_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Danh sách tất cả AI đang chạy"""
    try:
        nodes = db.get_all_nodes()
        
        if not nodes:
            await update.message.reply_text(
                "📜 Hiện không có AI nào đang chạy.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
        
        list_text = f"📜 *Danh Sách AI Đang Chạy* ({len(nodes)} total)\n\n"
        
        for node in nodes:
            status_icon = "🟢" if node["status"] == "online" else "🔴"
            list_text += f"""{status_icon} ID: `{node['chat_id']}`
   Model: {node['model']} | Requests: {node['requests']} | Tokens: {node['tokens']:,}

"""
        
        await update.message.reply_text(
            list_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in list_all_ai: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem thống kê"""
    try:
        chat_id = update.effective_chat.id
        
        stats = db.get_usage_stats(chat_id, hours=24)
        
        if not stats:
            await update.message.reply_text(
                "📈 Chưa có dữ liệu thống kê.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
        
        stats_text = f"""
📈 *Thống Kê Sử Dụng (24h)*

📊 Tổng Requests: {stats['total_requests']}
🔤 Tổng Tokens: {stats['total_tokens']:,}
⏱️ Avg Response Time: {stats['avg_response_time_ms']:.2f}ms
❌ Lỗi: {stats['error_count']}
"""
        
        await update.message.reply_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in show_stats: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def show_vps_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trạng thái VPS"""
    try:
        import subprocess
        
        # Lấy thông tin từ API gateway
        status_text = f"""
⚡ *Trạng Thái VPS*

🟢 Gateway API: Hoạt động
📡 Tailscale Funnel: Hoạt động
🔗 Endpoint: https://vps.tail3ddee5.ts.net

📊 Nodes Đang Chạy: {len(db.get_all_nodes())}
🟢 Online: {len([n for n in db.get_all_nodes() if n['status'] == 'online'])}
🔴 Offline: {len([n for n in db.get_all_nodes() if n['status'] == 'offline'])}

⏱️ Cập nhật: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await update.message.reply_text(
            status_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in show_vps_status: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Làm mới"""
    try:
        chat_id = update.effective_chat.id
        db.update_user_activity(chat_id)
        
        await update.message.reply_text(
            "🔄 Đã làm mới dữ liệu.",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in refresh: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def delete_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xóa AI - Bước 1: Xác nhận"""
    try:
        chat_id = update.effective_chat.id
        
        node = db.get_node(chat_id)
        if not node:
            await update.message.reply_text(
                "❌ Bạn không có AI nào để xóa.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
        
        confirm_text = f"""
⚠️ *Xác Nhận Xóa AI*

Bạn có chắc muốn xóa AI này?

Model: {node['model']}
Requests: {node['requests']}
Tokens: {node['tokens']:,}

Hành động này không thể hoàn tác!
"""
        
        keyboard = [
            ["✅ Xóa", "❌ Hủy"]
        ]
        
        await update.message.reply_text(
            confirm_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
        return DELETE_AI_CONFIRM
    
    except Exception as e:
        logger.error(f"Error in delete_ai: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def delete_ai_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xóa AI - Bước 2: Thực hiện xóa"""
    try:
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        if message_text == "❌ Hủy":
            await update.message.reply_text(
                "Đã hủy xóa AI.",
                reply_markup=get_main_menu_keyboard()
            )
            return MENU_STATE
        
        # Xóa node và API key
        db.delete_node(chat_id)
        db.deactivate_api_key(chat_id)
        
        # Cancel workflow nếu có
        api_key_info = db.get_api_key_by_chat_id(chat_id)
        if api_key_info and api_key_info.get("run_id") and github_manager:
            github_manager.cancel_workflow_run(int(api_key_info["run_id"]))
        
        await update.message.reply_text(
            "✅ AI đã được xóa thành công.",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in delete_ai_confirm: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cài đặt"""
    try:
        settings_text = """
⚙️ *Cài Đặt*

- 🔐 Bảo mật: API Key được mã hóa
- 💾 Database: SQLite
- 🌐 API Gateway: Flask
- 🤖 Bot: python-telegram-bot
- ☁️ Compute: GitHub Actions
- 🏃 Runtime: Ollama

Liên hệ: @sun_forge

"""
        
        await update.message.reply_text(
            settings_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU_STATE
    
    except Exception as e:
        logger.error(f"Error in settings: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return MENU_STATE

# ============ Error Handler ============

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# ============ Main ============

def main():
    """Main function"""
    # Lấy token từ environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN không được cấu hình")
    
    # Tạo application
    application = Application.builder().token(token).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)
            ],
            CREATE_AI_SELECT_MODEL: [
                MessageHandler(filters.TEXT, create_ai_select_model)
            ],
            CONFIRM_CREATE: [
                MessageHandler(filters.TEXT, confirm_create_ai)
            ],
            DELETE_AI_CONFIRM: [
                MessageHandler(filters.TEXT, delete_ai_confirm)
            ],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    # Start bot
    print("=" * 50)
    print("SUN AI - Telegram Bot")
    print("=" * 50)
    print("🚀 Bot đang chạy...")
    print("=" * 50)
    
    application.run_polling()

if __name__ == "__main__":
    main()
