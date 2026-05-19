"""
config.py — Token, API key, hằng số toàn cục
"""
import os
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent
_SECRETS_TXT = _BASE_DIR / os.getenv("SECRETS_FILE", "secrets.txt")

def _parse_secrets_txt(path: Path) -> tuple[str | None, list[str], list[str]]:
    """Đọc secrets.txt — bot:, groq:, openrouter: (mỗi dòng = một key)."""
    bot_token = None
    groq_keys: list[str] = []
    openrouter_keys: list[str] = []
    if not path.is_file():
        return bot_token, groq_keys, openrouter_keys

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        name, _, value = line.partition(":")
        name = name.strip().lower()
        value = value.strip()
        if not value:
            continue
        if name == "bot":
            bot_token = value
        elif name == "groq":
            groq_keys.append(value)
        elif name in ("openrouter", "or"):
            openrouter_keys.append(value)
    return bot_token, groq_keys, openrouter_keys


_TXT_BOT, _TXT_GROQ_KEYS, _TXT_OPENROUTER_KEYS = _parse_secrets_txt(_SECRETS_TXT)

# =========================
# BOT TOKEN & API KEYS — tự đọc từ secrets.txt khi chạy main.py
# =========================
BOT_TOKEN = _TXT_BOT
if not BOT_TOKEN:
    raise ValueError(
        f"Thiếu token Telegram. Tạo file {_SECRETS_TXT} với dòng:\n"
        f"  bot:7123456789:AAH..."
    )

if not _TXT_GROQ_KEYS and not _TXT_OPENROUTER_KEYS:
    raise ValueError(
        f"Thiếu API AI. Thêm vào {_SECRETS_TXT}:\n"
        f"  groq:gsk_...\n"
        f"  openrouter:sk-or-v1-..."
    )

# =========================
# OWNER & URLs
# =========================
OWNER_ID = 5860306667
RSS_URL = "https://vnexpress.net/rss/tin-moi-nhat.rss"
DOWNLOADS_DIR = "downloads"

# =========================
# AI: Groq → OpenRouter (OpenAI SDK)
# =========================
from utils.ai_client import AI_AVAILABLE, generate_ai_chat, init_ai_providers

init_ai_providers(_TXT_GROQ_KEYS, _TXT_OPENROUTER_KEYS)
ai_model = AI_AVAILABLE  # tương thích code cũ: if ai_model

# Tạo thư mục downloads nếu chưa có
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# =========================
# QUOTES (Đạo lý)
# =========================
QUOTES = [
    "Sống không phải để tồn tại, mà là để vươn tới, để chinh phục.",
    "Sự chăm chỉ là mẹ của may mắn.",
    "Không có gì là không thể với một trái tim sẵn sàng và một bộ não không ngừng học hỏi.",
    "Tôi không già đi, tôi chỉ thăng cấp thôi.",
    "Tôi đã cố gắng giảm cân. Nhưng rồi tôi nhận ra tôi yêu đồ ăn hơn là yêu cơ thể mình.",
    "Cuộc sống là sự cân bằng giữa việc nắm giữ và buông bỏ.",
    "Không có gì có thể dập tắt ánh sáng từ bên trong bạn.",
    "Sự bình yên đến từ bên trong. Đừng tìm kiếm nó bên ngoài.",
    "Sống ảo không xấu, xấu là khi bạn quên mất mình đang sống thật.",
    "Bạn mạnh mẽ hơn bạn nghĩ, và có thể làm được nhiều hơn bạn tưởng.",
    "Nếu cuộc sống cho bạn chanh, hãy làm nước chanh. Nếu cho cục đá, hãy phàn nàn về nó trên mạng xã hội.",
    "Cuộc đời ngắn lắm, hãy cười khi bạn vẫn còn răng.",
    "Tôi không lười, tôi chỉ đang ở chế độ tiết kiệm năng lượng.",
    "Tiền không mua được hạnh phúc, nhưng mua được trà sữa và trà sữa thì gần giống hạnh phúc.",
    "Già đi là bắt buộc, trưởng thành là tùy chọn.",
    "Đừng bao giờ từ bỏ giấc mơ. Hãy ngủ thêm tí nữa.",
    "Thành công lớn nhất là đứng dậy sau mỗi lần vấp ngã.",
    "Đời ngắn lắm, đừng phí thời gian sống theo cách người khác muốn.",
    "Muốn thành công thì khao khát thành công phải lớn hơn nỗi sợ thất bại.",
    "Không ai giàu ba họ, không ai khó ba đời, nhưng lười thì cả đời vẫn nghèo.",
    "Đừng sợ thất bại, hãy sợ việc không cố gắng.",
    "Cà phê đắng, cuộc đời cũng đắng, nhưng có đường thì ngọt ngay.",
    "Đừng so sánh mình với người khác, họ là phiên bản beta, bạn là bản limited.",
    "Tuổi trẻ là hữu hạn, ngu thì vô hạn.",
    "Người ta yêu nhau có đôi có cặp, còn tôi chỉ có đôi dép với cái quạt.",
    "Đừng buồn vì cô đơn, ít nhất bạn còn có Wi-Fi.",
    "Hạnh phúc không phải là đích đến, mà là cách bạn đi.",
    "Đừng tìm người hoàn hảo, hãy tìm người hợp với mình là được.",
    "Người thông minh giải quyết vấn đề, người khôn ngoan tránh được vấn đề, còn tôi thì tạo ra vấn đề mới.",
    "Đừng tin lời hứa, hãy tin vào hành động. Đừng tin hành động, hãy tin vào chuyển khoản.",
    "Yêu đơn phương giống như ăn mì gói không có gói gia vị, nhạt nhẽo nhưng vẫn cố nuốt.",
    "Người yêu cũ giống như bài kiểm tra cũ, nhìn lại chỉ thấy sai đầy ra.",
    "Đừng cố gắng làm hài lòng tất cả, mẹ bạn cũng không làm được.",
    "Đừng sợ cô đơn, sợ nhất là ở cạnh người mà vẫn cô đơn.",
    "Đừng bao giờ bỏ cuộc, trừ khi đó là bỏ ngủ trưa.",
    "Đừng hỏi tại sao tôi độc thân, hãy hỏi tại sao bạn chưa đủ tiêu chuẩn.",
    "Thà khóc trong BMW còn hơn cười trên xe đạp. À không, cười trên xe đạp vui hơn nhiều.",
    "Đừng buồn khi không ai nhớ tới sinh nhật bạn, ít nhất Google còn nhớ.",
    "Người ta gọi là crush vì crush xong là tan nát.",
    "Đừng bao giờ tin lời đàn ông, trừ khi đó là 'anh chuyển khoản rồi đây'.",
    "Hạnh phúc là khi mẹ không hỏi 'khi nào cưới?'.",
    "Đừng sợ thất nghiệp, sợ nhất là thất tình.",
    "Người yêu cũ nhắn tin lại = hết tiền tiêu.",
    "Cuộc sống giống như Facebook, ai cũng chỉ khoe những điều đẹp đẽ nhất.",
    "Thà làm người thất bại vui vẻ còn hơn làm người thành công buồn chán.",
    "Đừng cố gắng làm hài lòng tất cả, bạn không phải trà sữa trân châu đường đen.",
    "Đừng buồn khi bị block, ít nhất bạn cũng từng được add.",
    "Đừng cố gắng trở thành người khác, hãy trở thành phiên bản giàu hơn của chính mình.",
    "Hạnh phúc là khi crush thả tim story bạn đăng lúc 3 giờ sáng.",
    "Đừng buồn khi không có người yêu, ít nhất bạn còn có Netflix.",
    "Đừng cố gắng trở thành người khác, hãy trở thành phiên bản không photoshop của chính mình.",
    "Người yêu cũ giống như quần áo lỗi mốt, có nhớ cũng không mặc lại.",
    "Đừng cố gắng làm hài lòng tất cả, bạn không phải là buffet.",
    "Hạnh phúc là khi mẹ không hỏi 'khi nào lấy vợ/chồng?'.",
    "Đừng sợ già, sợ nhất là già mà vẫn nghèo.",
    "Người ta yêu nhau bằng tai, bằng mắt, còn tôi yêu bằng mũi – ngửi thấy mùi đồ ăn là yêu luôn.",
    "Tình yêu em nhiều lắm, nhưng yêu đồ ăn còn nhiều hơn.",
    "Đừng cố gắng làm người quan trọng với tất cả, bạn không phải là oxygen.",
    "Đừng buồn khi bị ghost, ít nhất bạn cũng từng được hiện hình.",
    "Hạnh phúc là khi mẹ không hỏi 'lương tháng này bao nhiêu?'.",
    "Cuộc sống giống như cái quần jeans, càng cũ càng đẹp.",
    "Đừng cố gắng thay đổi người khác, hãy thay đổi pass Wi-Fi đi.",
    "Đừng sợ thất bại, sợ nhất là hết tiền mà vẫn còn đói.",
    "Người yêu cũ nhắn tin lại không phải vì nhớ bạn, mà vì nhớ tiền bạn.",
    "Đừng cố gắng làm hài lòng tất cả, bạn không phải là iPhone mới ra.",
    "Hạnh phúc là khi crush nhớ sinh nhật bạn mà không cần Facebook nhắc.",
    "Đừng cố gắng hiểu đàn ông, hãy cố gắng yêu thương họ.",
    "Đừng cố gắng hiểu phụ nữ, hãy cố gắng yêu thương họ.",
    "Đừng sợ cô đơn, hãy tận hưởng nó trước khi có người làm phiền.",
    "Đừng cố gắng trở thành người khác, hãy trở thành phiên bản tốt nhất của chính mình.",
    "Hạnh phúc không phải là có tất cả, mà là biết đủ với những gì mình có.",
    "Cuộc sống giống như một ly cà phê, đắng trước ngọt sau.",
    "Đừng buồn vì quá khứ, hãy vui vì bạn đã sống sót qua nó.",
    "Đừng sợ cô đơn, đó là cơ hội để bạn gặp gỡ chính mình.",
    "Đừng cố gắng làm người khác hạnh phúc nếu bạn còn chưa hạnh phúc.",
    "Hạnh phúc là khi bạn ngừng so sánh và bắt đầu biết ơn.",
    "Đừng sợ thất bại, đó chỉ là cách cuộc sống dạy bạn cách bay cao hơn.",
    "Cuộc sống giống như một cuốn sách, mỗi ngày là một trang mới.",
    "Đừng buồn khi không ai hiểu bạn, ít nhất bạn còn hiểu chính mình.",
    "Hạnh phúc là khi bạn ngừng chạy theo và bắt đầu sống.",
    "Đừng cố gắng làm hài lòng tất cả, bạn không phải là cái nút like.",
    "Cuộc đời giống như một con đường, có lúc thẳng lúc cong, quan trọng là vẫn đi tiếp.",
    "Đừng sợ cô đơn, đó là lúc bạn mạnh mẽ nhất.",
    "Hạnh phúc là khi bạn biết buông tay đúng lúc.",
    "Đừng cố gắng làm hài lòng tất cả, bạn không phải là cái máy ATM.",
    "Cuộc sống giống như một cơn mưa, sau cơn mưa trời lại sáng.",
    "Đừng buồn vì những gì đã mất, hãy vui vì những gì còn lại.",
    "Hạnh phúc là khi bạn cười mà không cần lý do.",
    "Đừng cố gắng trở thành người khác, hãy trở thành người mà bạn tự hào về chính mình.",
    "Cuộc đời giống như một bữa tiệc, nhớ ăn no trước khi về.",
    "Đừng sợ cô đơn, đó là lúc bạn tìm thấy chính mình.",
    "Hạnh phúc là khi bạn sống đúng với trái tim mình.",
    "Cuộc sống giống như một bức tranh, bạn chính là người cầm cọ.",
    "Đừng sợ thất bại, đó là học phí cho thành công lớn hơn.",
    "Hạnh phúc là khi bạn tìm thấy bình yên giữa cơn bão cuộc đời.",
    "Đừng cố gắng làm hài lòng tất cả, bạn không phải là cái nút tim.",
    "Cuộc đời giống như một ly trà sữa, càng hút càng nghiện.",
    "Hạnh phúc là khi bạn cười mà mắt cũng cười theo.",
    "Đừng buồn khi bị tổn thương, đó là cách cuộc sống dạy bạn trân trọng.",
    "Hạnh phúc là khi bạn sống đúng với chính mình, không cần giả vờ."
]

# =========================
# QUIZ QUESTIONS
# =========================
QUIZ_QUESTIONS = [
    {"q": "Thủ đô của Pháp là gì?", "a": "paris"},
    {"q": "2 + 2 = ?", "a": "4"},
    {"q": "Màu bầu trời ban ngày?", "a": "xanh"}
]
