"""
handlers/caro.py — Game Caro: commands, callbacks, helpers, callback_router
"""
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import OWNER_ID
from database import (
    games, session_scores, caro_scores,
    get_caro_score, record_caro_result, get_db_connection,
    get_global_caro_ranking, get_user_display_name,
    clear_caro_scores_for_chat,
)
from utils.helpers import get_member_name, resolve_user_identifier, is_board_full
import sqlite3


def generate_board_id(chat_id: int) -> str:
    return f"{chat_id}_{int(datetime.now().timestamp()*1000)}_{random.randint(1000, 9999)}"


def ensure_session(session_id, player_x, player_o=None):
    session = session_scores.setdefault(session_id, {"player_x": player_x, "player_o": player_o, "wins": {}})
    session["player_x"] = player_x
    if player_o:
        session["player_o"] = player_o
    for pid in [session["player_x"], session.get("player_o")]:
        if pid:
            session["wins"].setdefault(pid, 0)
    return session


def build_caro_button_rows(board_id, board, size, last_row=None, last_col=None, win_cells=None):
    rows = []
    win_set = set(win_cells) if win_cells else set()
    show_numbers = size <= 7
    if show_numbers:
        header = [InlineKeyboardButton(" ", callback_data="caro_none")]
        for c in range(size):
            header.append(InlineKeyboardButton(str(c + 1), callback_data="caro_none"))
        rows.append(header)
    for r in range(size):
        row = []
        if show_numbers:
            row.append(InlineKeyboardButton(str(r + 1), callback_data="caro_none"))
        for c in range(size):
            cell = board[r][c]
            label = "❌" if cell == 'X' else ("⭕" if cell == 'O' else "ㅤ")
            is_highlight = (r, c) in win_set or (
                win_set == set() and last_row is not None and last_col is not None
                and r == last_row and c == last_col
            )
            btn = InlineKeyboardButton(
                label,
                callback_data=f"caro_game|{board_id}|{r}|{c}",
                style="primary" if is_highlight else None,
            )
            row.append(btn)
        rows.append(row)
    return rows


def make_caro_keyboard_dynamic(board_id, board, size, extra_rows=None, last_row=None, last_col=None, win_cells=None):
    rows = build_caro_button_rows(board_id, board, size, last_row=last_row, last_col=last_col, win_cells=win_cells)
    if extra_rows:
        rows.extend(extra_rows)
    return InlineKeyboardMarkup(rows)


def build_caro_display_text(
    game,
    player_x_name,
    player_o_name,
    chat_id,
    extra_note=None,
    *,
    game_over: bool = False,
):
    size = game['size']
    win_count = game['win_count']
    lines = []
    if size == 3 and game.get('session_id'):
        session = ensure_session(game['session_id'], game['player_x'], game.get('player_o'))
        lines.append("👾 Caro 3x3")
        wins_map = session["wins"]
        lines.append(f"Người chơi 1: {player_x_name}")
        lines.append(f"Win: {wins_map.get(game['player_x'], 0)}")
        if game.get('player_o'):
            opponent = player_o_name if player_o_name else "player 2"
            lines.append(f"Người chơi 2: {opponent}")
            lines.append(f"Win: {wins_map.get(game['player_o'], 0)}")
        else:
            lines.append("Người chơi 2: Chưa có đối thủ")
        lines.append("")
    else:
        lines.append(f"🎮 Caro {size}x{size} - {win_count} ô để thắng")
    opponent_display = player_o_name if player_o_name else "player 2"
    lines.append(f"{player_x_name} (X) vs {opponent_display} (O)")
    if not game_over:
        if game.get('last_turn') is not None:
            last_player = player_x_name if game['last_turn'] == 'X' else opponent_display
            lines.append(f"Last turn: {last_player} : hàng {game['last_row'] + 1}, cột {game['last_col'] + 1}")
        current_player = player_x_name if game['current'] == 'X' else opponent_display
        lines.append(f"Đến lượt của :{current_player}")
    if extra_note:
        lines.append("")
        lines.append(extra_note)
    return "\n".join(lines).strip()


def create_caro_game(chat_id, size, win_count, player_x_id, player_o_id=None, board_id=None, session_id=None):
    board = [[" " for _ in range(size)] for _ in range(size)]
    board_id = board_id or generate_board_id(chat_id)
    games[board_id] = {
        'board_id': board_id, 'board': board, 'current': 'X',
        'player_x': player_x_id, 'player_o': player_o_id,
        'chat_id': chat_id, 'last_turn': None, 'last_row': None, 'last_col': None,
        'size': size, 'win_count': win_count, 'session_id': session_id
    }
    return games[board_id]


def check_winner_dynamic(board, size, win_count):
    for r in range(size):
        for c in range(size - win_count + 1):
            if board[r][c] != " " and all(board[r][c + i] == board[r][c] for i in range(win_count)):
                return board[r][c], [(r, c + i) for i in range(win_count)]
    for c in range(size):
        for r in range(size - win_count + 1):
            if board[r][c] != " " and all(board[r + i][c] == board[r][c] for i in range(win_count)):
                return board[r][c], [(r + i, c) for i in range(win_count)]
    for r in range(size - win_count + 1):
        for c in range(size - win_count + 1):
            if board[r][c] != " " and all(board[r + i][c + i] == board[r][c] for i in range(win_count)):
                return board[r][c], [(r + i, c + i) for i in range(win_count)]
    for r in range(win_count - 1, size):
        for c in range(size - win_count + 1):
            if board[r][c] != " " and all(board[r - i][c + i] == board[r][c] for i in range(win_count)):
                return board[r][c], [(r - i, c + i) for i in range(win_count)]
    return None, None


async def start_caro_board_from_callback(query, context, size, win_count, player_x_id=None, player_o_id=None, session_id=None):
    chat_id = query.message.chat.id
    player_x_id = player_x_id or query.from_user.id
    if size == 3:
        session_id = session_id or f"{chat_id}_{query.message.message_id}"
        ensure_session(session_id, player_x_id, player_o_id)
    game = create_caro_game(chat_id, size, win_count, player_x_id, player_o_id, session_id=session_id)
    player_x_name = query.from_user.full_name if player_x_id == query.from_user.id else await get_member_name(context, chat_id, player_x_id, "Player 1")
    player_o_name = await get_member_name(context, chat_id, player_o_id, "Player 2") if player_o_id else None
    kb = make_caro_keyboard_dynamic(game['board_id'], game['board'], size)
    display_text = build_caro_display_text(game, player_x_name, player_o_name, chat_id)
    await query.edit_message_text(display_text, reply_markup=kb)


async def caro_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("3x3 (3 ô thắng)", callback_data="caro_size|3")],
        [InlineKeyboardButton("4x4 (3 ô thắng)", callback_data="caro_size|4")],
        [InlineKeyboardButton("5x5 (3 ô thắng)", callback_data="caro_size|5")],
        [InlineKeyboardButton("6x6", callback_data="caro_size|6")],
        [InlineKeyboardButton("7x7", callback_data="caro_size|7")],
        [InlineKeyboardButton("8x8", callback_data="caro_size|8")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"🎮 Chọn kích thước bàn cờ, {user.full_name}!", reply_markup=reply_markup)
    try:
        await update.message.delete()
    except:
        pass


async def xo_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text('❌ Reply người khác để chơi Caro!')
        return
    challenger = update.effective_user
    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    if challenger.id == OWNER_ID:
        first_player, second_player = challenger, target
    elif target.id == OWNER_ID:
        first_player, second_player = target, challenger
    else:
        first_player = random.choice([challenger, target])
        second_player = target if first_player == challenger else challenger
    game = create_caro_game(chat_id, 8, 5, first_player.id, second_player.id, board_id=generate_board_id(chat_id))
    kb = make_caro_keyboard_dynamic(game['board_id'], game['board'], 8)
    display_text = build_caro_display_text(game, first_player.full_name, second_player.full_name, chat_id)
    await update.message.reply_text(display_text, reply_markup=kb)


async def _resolve_rank_display_name(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int | None,
    user_id: int,
    fallback: str,
) -> str:
    saved = get_user_display_name(user_id)
    if saved:
        return saved
    if chat_id:
        try:
            return await get_member_name(context, chat_id, user_id, fallback)
        except Exception:
            pass
    try:
        tg_user = await context.bot.get_chat(user_id)
        return tg_user.full_name or tg_user.first_name or fallback
    except Exception:
        return fallback


async def rank_caro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bảng xếp hạng Caro, dùng được cả chat riêng."""
    chat = update.effective_chat
    chat_id = chat.id if chat and chat.type != "private" else None
    rows = get_global_caro_ranking()

    if not rows:
        await update.message.reply_text("😿 Chưa có dữ liệu Caro nào. Vào /caro chơi thử nha!")
        return

    ranking, prev_key, rank = [], None, 0
    for idx, (uid, wins, total) in enumerate(rows, start=1):
        key = (wins, total)
        if key != prev_key:
            rank = idx
            prev_key = key
        ranking.append((rank, uid, wins, total))

    top = ranking[:10]
    lines = ["🏆 Xếp hạng Caro:"]
    for rank_val, uid, wins, total in top:
        name = await _resolve_rank_display_name(context, chat_id, uid, f"User {uid}")
        lines.append(f"{rank_val}. {name} — {wins} điểm ({total} trận)")

    user_id = update.effective_user.id
    user_entry = next((item for item in ranking if item[1] == user_id), None)
    top_uids = {item[1] for item in top}
    if user_entry and user_id not in top_uids:
        rank_val, _, wins, total = user_entry
        lines.append("")
        lines.append(f"✨ Cậu đang hạng #{rank_val} với {wins} điểm ({total} trận).")
    elif not user_entry:
        lines.append("")
        lines.append("✨ Cậu chưa có trận nào, vào /caro chơi thử nha!")

    await update.message.reply_text("\n".join(lines))


async def set_caro_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not chat:
        return

    is_private = chat.type == "private"
    is_owner = user.id == OWNER_ID

    if is_private and not is_owner:
        await update.message.reply_text("⚠️ Lệnh /set chỉ dùng trong nhóm hoặc chat riêng với chủ bot.")
        return

    if not is_private:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if not is_owner and member.status not in ("administrator", "creator"):
            await update.message.reply_text("⛔ Chỉ admin mới được dùng lệnh này.")
            return

    chat_id = chat.id
    target_user, target_id, args = None, None, context.args
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_id = target_user.id
        if not args:
            await update.message.reply_text("Nhập số điểm cần set, ví dụ: /set 10")
            return
        point_arg = args[0]
    else:
        if len(args) < 2:
            await update.message.reply_text("Dùng: /set <@username|user_id> <điểm>")
            return
        point_arg = args[1]
        target_id = resolve_user_identifier(args[0])
        if not target_id:
            await update.message.reply_text("Không tìm thấy người cần set điểm.")
            return
    try:
        points = max(int(point_arg), 0)
    except ValueError:
        await update.message.reply_text("Điểm phải là số nguyên, ví dụ: /set 15")
        return
    stats = get_caro_score(target_id, chat_id)
    new_total = max(points, stats['total'])
    win_rate = (points / new_total * 100) if new_total else 0
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_caro_scores (user_id, chat_id, caro_wins, total_games, win_rate, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, chat_id) DO UPDATE SET
                    caro_wins = excluded.caro_wins,
                    total_games = excluded.total_games,
                    win_rate = excluded.win_rate,
                    last_updated = CURRENT_TIMESTAMP
                """,
                (target_id, chat_id, points, new_total, win_rate),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            print(f"Lỗi DB (/set): {e}")
    chat_scores_map = caro_scores.setdefault(chat_id, {})
    chat_scores_map[target_id] = {"wins": points, "total": new_total}
    target_name = target_user.full_name if target_user else await get_member_name(context, chat_id, target_id, f"User {target_id}")
    await update.message.reply_text(f"✅ Đã set {points} điểm Caro cho {target_name}.")


async def reset_caro_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /reset — xóa toàn bộ điểm Caro của nhóm (chỉ admin hoặc chủ bot)."""
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("⚠️ Lệnh /reset chỉ dùng trong nhóm.")
        return
    chat_id = chat.id
    user = update.effective_user
    member = await context.bot.get_chat_member(chat_id, user.id)
    if user.id != OWNER_ID and member.status not in ("administrator", "creator"):
        await update.message.reply_text("⛔ Chỉ admin hoặc chủ bot mới được reset bảng điểm.")
        return
    deleted = clear_caro_scores_for_chat(chat_id)
    await update.message.reply_text(
        f"🧹 Đã reset bảng điểm Caro của nhóm này ({deleted} bản ghi trong DB).\n"
        "Điểm trên /rank (tổng) cũng bớt phần đóng góp từ nhóm này."
    )


async def caro_size_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data.split('|')
    if data[0] != 'caro_size':
        return
    size = int(data[1])
    if size <= 5:
        await start_caro_board_from_callback(query, context, size, 3)
        return
    keyboard = [
        [InlineKeyboardButton("3 ô liên tục", callback_data=f"caro_win|{size}|3")],
        [InlineKeyboardButton("4 ô liên tục", callback_data=f"caro_win|{size}|4")],
        [InlineKeyboardButton("5 ô liên tục", callback_data=f"caro_win|{size}|5")]
    ]
    await query.edit_message_text(f"🎮 Kích thước: {size}x{size}\n\nChọn số ô liên tục để thắng!", reply_markup=InlineKeyboardMarkup(keyboard))


async def caro_win_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data.split('|')
    if data[0] != 'caro_win':
        return
    await start_caro_board_from_callback(query, context, int(data[1]), int(data[2]))


async def caro_game_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data.split('|')
    if data[0] not in ('caro_game', 'caro8'):
        return
    board_id, r, c = data[1], int(data[2]), int(data[3])
    game = games.get(board_id)
    if not game:
        await query.answer('Game ended⭐️', show_alert=True)
        return
    user_id = query.from_user.id
    size = game.get('size', 8)
    win_count = game.get('win_count', 5)
    session_id = game.get('session_id')
    if size == 3 and session_id:
        ensure_session(session_id, game['player_x'], game.get('player_o'))
    if game['current'] == 'X' and user_id != game['player_x']:
        await query.answer('Not your turn!', show_alert=True)
        return
    if game['current'] == 'O':
        if not game['player_o']:
            game['player_o'] = user_id
            if size == 3 and session_id:
                ensure_session(session_id, game['player_x'], user_id)
        elif user_id != game['player_o']:
            await query.answer('Not your turn!', show_alert=True)
            return
    if game['board'][r][c] != " ":
        await query.answer('Occupied!', show_alert=True)
        return
    game['board'][r][c] = game['current']
    player_x_name = await get_member_name(context, game['chat_id'], game['player_x'], "Player 1")
    player_o_name = await get_member_name(context, game['chat_id'], game.get('player_o'), "player 2") if game.get('player_o') else None
    winner, win_cells = check_winner_dynamic(game['board'], size, win_count)
    draw = False
    result_note = None
    if winner:
        winner_name = player_x_name if winner == 'X' else (player_o_name or "player 2")
        result_note = f"👑 {winner_name} đã thắng trận!"
        if game.get('player_o'):
            if winner == 'X':
                record_caro_result(game['chat_id'], winner_id=game['player_x'], loser_id=game['player_o'])
            else:
                record_caro_result(game['chat_id'], winner_id=game['player_o'], loser_id=game['player_x'])
        if size == 3 and session_id:
            session = ensure_session(session_id, game['player_x'], game.get('player_o'))
            winner_id = game['player_x'] if winner == 'X' else game.get('player_o')
            if winner_id:
                session['wins'][winner_id] = session['wins'].get(winner_id, 0) + 1
    elif is_board_full(game['board']):
        draw = True
        result_note = "🤝 Hòa kèo!"
        if game.get('player_o'):
            record_caro_result(game['chat_id'], draw_players=[game['player_x'], game['player_o']])
    if winner or draw:
        extra_rows = None
        if size == 3 and game.get('player_o') and game.get('session_id'):
            sid = game['session_id']
            extra_rows = [
                [InlineKeyboardButton("Chơi lại", callback_data=f"caro3_action|retry|{sid}|{game['player_x']}|{game['player_o']}")],
                [InlineKeyboardButton("Kết thúc", callback_data=f"caro3_action|end|{sid}")]
            ]
        kb = make_caro_keyboard_dynamic(
            board_id, game['board'], size,
            extra_rows=extra_rows,
            win_cells=win_cells if winner else None,
        )
        display_text = build_caro_display_text(
            game, player_x_name, player_o_name, game['chat_id'], result_note, game_over=True
        )
        await query.edit_message_text(display_text, reply_markup=kb)
        del games[board_id]
        return
    game['last_turn'] = game['current']
    game['last_row'] = r
    game['last_col'] = c
    game['current'] = 'O' if game['current'] == 'X' else 'X'
    kb = make_caro_keyboard_dynamic(
        board_id, game['board'], size,
        last_row=game['last_row'],
        last_col=game['last_col'],
    )
    display_text = build_caro_display_text(game, player_x_name, player_o_name, game['chat_id'])
    await query.edit_message_text(display_text, reply_markup=kb)


async def caro3_action_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data.split('|')
    if data[0] != 'caro3_action':
        return
    action = data[1]
    if action == "retry":
        session_id = data[2]
        player_x_id = int(data[3])
        player_o_id = int(data[4]) if len(data) > 4 else 0
        if not player_o_id:
            await query.answer("Chưa có người chơi thứ hai!", show_alert=True)
            return
        chat_id = query.message.chat.id
        ensure_session(session_id, player_x_id, player_o_id)
        game = create_caro_game(chat_id, 3, 3, player_x_id, player_o_id, board_id=generate_board_id(chat_id), session_id=session_id)
        player_x_name = await get_member_name(context, chat_id, player_x_id, "Player 1")
        player_o_name = await get_member_name(context, chat_id, player_o_id, "Player 2")
        kb = make_caro_keyboard_dynamic(game['board_id'], game['board'], 3)
        display_text = build_caro_display_text(game, player_x_name, player_o_name, chat_id)
        await query.edit_message_text(display_text, reply_markup=kb)
    else:
        session_id = data[2] if len(data) > 2 else None
        session = session_scores.get(session_id)
        if session:
            chat_id = query.message.chat.id
            wins = session["wins"]
            px, po = session.get("player_x"), session.get("player_o")
            p1 = await get_member_name(context, chat_id, px, "Người chơi 1")
            p2 = await get_member_name(context, chat_id, po, "Người chơi 2") if po else "Người chơi 2"
            summary = f"🏁 Tổng kết phiên Caro 3x3:\n- {p1}: {wins.get(px, 0)} win\n- {p2}: {wins.get(po, 0)} win"
        else:
            summary = "🏁 Phiên đã kết thúc."
        await query.edit_message_text(summary)
        session_scores.pop(session_id, None)


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router cho tất cả callback queries"""
    data = update.callback_query.data
    if data in ("none", "caro_none"):
        await update.callback_query.answer()
        return
    elif data.startswith('caro_size|'):
        await caro_size_callback(update, context)
    elif data.startswith('caro_win|'):
        await caro_win_callback(update, context)
    elif data.startswith('caro3_action|'):
        await caro3_action_callback(update, context)
    elif data.startswith('caro_game|') or data.startswith('caro8|'):
        await caro_game_callback(update, context)
