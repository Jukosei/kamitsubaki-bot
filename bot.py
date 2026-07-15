import discord
from PIL import Image, ImageDraw, ImageFont
from keep_alive import keep_alive
import os
import io
import base64
import re
from collections import Counter

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

CARDS_DIR = "./cards"  # カード画像を保存しているフォルダ

def decode_kcg_code(kcg_code: str) -> list:
    """KCG-から始まる非公式コードをカードIDのリストにデコードする"""
    clean_code = kcg_code.strip()
    if clean_code.startswith("KCG-"):
        clean_code = clean_code[4:]
    
    try:
        missing_padding = len(clean_code) % 4
        if missing_padding:
            clean_code += '=' * (4 - missing_padding)
            
        decoded_bytes = base64.b64decode(clean_code)
        deck_text = decoded_bytes.decode('utf-8')
        return [cid.strip() for cid in deck_text.split("/") if cid.strip()]
    except Exception as e:
        raise ValueError(f"KCGコードの解読に失敗しました: {e}")

def generate_official_like_image(card_ids: list, card_counts: Counter, unique_card_ids: list, original_code: str) -> io.BytesIO:
    """公式HP風のベージュ背景・額縁が入ったデッキ画像を生成する（カードの間に隙間を空ける修正版）"""
    card_w, card_h = 135, 185  # カードサイズ
    number_area_h = 35         # 数字枠の高さ
    
    # カード同士の「隙間（間隔）」を設定
    gap_x = 10  # 横の隙間（10ピクセル）
    gap_y = 15  # 縦の隙間（15ピクセル）
    
    # 1マス（カード＋数字エリア）の総高さ
    slot_h = card_h + number_area_h + gap_y

    max_cols = 10
    total_unique_cards = len(unique_card_ids)
    rows = (total_unique_cards + max_cols - 1) // max_cols

    # 外周の余白調整
    top_margin = 60    # 上部余白
    side_margin = 60   # 左右余白
    bottom_margin = 60 # 下部余白

    # 隙間の分を含めて、全体のキャンバスサイズを正確に計算
    canvas_w = (card_w * max_cols) + (gap_x * (max_cols - 1)) + (side_margin * 2)
    canvas_h = top_margin + (slot_h * rows) - gap_y + bottom_margin

    # 1. 公式風の高級感のあるベージュ背景画像を作成 (RGB)
    deck_canvas = Image.new("RGB", (canvas_w, canvas_h), (250, 247, 240))
    draw = ImageDraw.Draw(deck_canvas)

    # 2. 飾り枠（額縁線）の描画
    border_offset = 20
    draw.rectangle(
        [border_offset, border_offset, canvas_w - border_offset, canvas_h - border_offset],
        outline=(205, 190, 170), width=2
    )
    # 内側の細い線
    draw.rectangle(
        [border_offset + 6, border_offset + 6, canvas_w - (border_offset + 6), canvas_h - (border_offset + 6)],
        outline=(225, 215, 200), width=1
    )

    # 3. フォントの読み込み
    def get_font(size, is_bold=False):
        font_names = ["msmeiryo.ttc", "msgothic.ttc", "arialbd.ttf"] if is_bold else ["msmeiryo.ttc", "msgothic.ttc", "arial.ttf"]
        for name in font_names:
            try:
                return ImageFont.truetype(name, size)
            except IOError:
                continue
        return ImageFont.load_default()

    font_num = get_font(26, is_bold=True)

    # 4. カードと枚数を順番に配置
    for index, card_id in enumerate(unique_card_ids):
        col = index % max_cols
        row = index // max_cols
        
        # 横の隙間（gap_x）と縦の隙間（slot_h）を計算に含めて配置座標を決定
        x = side_margin + (col * (card_w + gap_x))
        y = top_margin + (row * slot_h)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
card_path = os.path.join(BASE_DIR, f"{card_id}.png")
        
        # --- カード画像のペースト ---
        if os.path.exists(card_path):
            with Image.open(card_path) as card_img:
                card_img = card_img.resize((card_w, card_h), Image.Resampling.LANCZOS)
                deck_canvas.paste(card_img, (x, y))
        else:
            error_box = Image.new("RGB", (card_w, card_h), (115, 105, 95))
            deck_canvas.paste(error_box, (x, y))

        # --- 下部の枚数表示エリア ---
        num_box_y = y + card_h + 6
        box_padding = 10
        box_x1 = x + box_padding
        box_x2 = x + card_w - box_padding
        box_y1 = num_box_y
        box_y2 = num_box_y + number_area_h
        
        draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=(255, 255, 255), outline=(220, 210, 195))
        
        # 枚数の数字
        count_text = str(card_counts[card_id])
        
        # ★タプルから [2] - [0] を引いて正確な幅と高さを出すように修正
        n_box = draw.textbbox((0, 0), count_text, font=font_num)
        text_w = n_box[2] - n_box[0]
        text_h = n_box[3] - n_box[1]
        
        text_x = box_x1 + ((box_x2 - box_x1) - text_w) // 2
        text_y = box_y1 + ((box_y2 - box_y1) - text_h) // 2 - 4
        
        draw.text((text_x, text_y), count_text, fill=(60, 55, 50), font=font_num)

    # 5. 最下部に公式風のフッターロゴ文字を配置
    font_code = get_font(20, is_bold=False)
    footer_text = "- KAMITSUBAKI CARD GAME -"
    f_box = draw.textbbox((0, 0), footer_text, font=font_code)
    # ★こちらもタプルから幅を正しく計算するように修正
    footer_w = f_box[2] - f_box[0]
    draw.text(((canvas_w - footer_w) // 2, canvas_h - 45), footer_text, fill=(180, 170, 155), font=font_code)

    # メモリ上で画像データを保存
    img_binary = io.BytesIO()
    deck_canvas.save(img_binary, format="JPEG", quality=90)
    img_binary.seek(0)
    return img_binary

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.event
async def on_message(message):
    # Bot自身の発言には反応しない（無限ループ防止）
    if message.author == client.user:
        return

    # メッセージの前後の余計な改行や空白を取り除く
    content = message.content.strip()
    
    # 完全に空白を詰めた判定用文字列を作成
    clean_content = content.replace("\n", "").replace(" ", "")
    
    card_ids = []
    is_deck_code = False

    # 1. 「KCG-」から始まるコードを自動検知
    # ★文字列に何が含まれていようが、頭文字が「KCG-」であれば「絶対に」反応するように修正しました！
    if clean_content.startswith("KCG-"):
        is_deck_code = True
        try:
            card_ids = decode_kcg_code(clean_content)
        except Exception as e:
            print(f"デコードエラー: {e}")
            return

    # 2. 「AA-01/exA-1」のようなスラッシュ区切りを自動検知
    elif "/" in clean_content:
        # スラッシュで区切る
        potential_ids = [cid.strip() for cid in clean_content.split("/") if cid.strip()]
        # IDらしき英数字や記号の塊が3枚以上並んでいれば通すルール
        if len(potential_ids) >= 3 and all(re.match(r"^[A-Za-z0-9\-\?\!]+$", cid) for cid in potential_ids):
            is_deck_code = True
            card_ids = potential_ids

    # デッキコードだと判別された場合の処理
    if is_deck_code and card_ids:
        try:
            await message.add_reaction("⏳")
        except discord.errors.Forbidden:
            pass

        try:
            # 枚数を集計
            card_counts = Counter(card_ids)
            unique_card_ids = list(card_counts.keys())

            # 公式風レイアウトで画像を生成
            img_data = generate_official_like_image(card_ids, card_counts, unique_card_ids, content)
            
            response_text = f"デッキコードを検出しました！（計 {len(card_ids)} 枚）"
            
            file = discord.File(fp=img_data, filename="kamitsubaki_deck.jpg")
            await message.reply(content=response_text, file=file)
            
        except Exception as e:
            await message.channel.send(f"画像の生成に失敗しました。: {e}")
            
        finally:
            try:
                await message.remove_reaction("⏳", client.user)
            except discord.errors.Forbidden:
                pass

import os
keep_alive()
client.run(os.getenv('DISCORD_BOT_TOKEN'))
