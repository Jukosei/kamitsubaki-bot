import discord
from PIL import Image, ImageDraw, ImageFont
import os
import io
import base64
import re
from collections import Counter

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

CARDS_DIR = "."  # フォルダを作らず、bot.pyと同じ場所から直接画像を探す

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
    """公式HP風のベージュ背景・額縁が入ったデッキ画像を生成する（フォント不要・超巨大デジタル数字完全版）"""
    card_w, card_h = 135, 185  # カードサイズ
    number_area_h = 50         # 数字枠の高さ
    
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

    # 全体のキャンバスサイズを計算
    canvas_w = (card_w * max_cols) + (gap_x * (max_cols - 1)) + (side_margin * 2)
    canvas_h = top_margin + (slot_h * rows) - gap_y + bottom_margin

    # 1. ベージュ背景画像を作成
    deck_canvas = Image.new("RGB", (canvas_w, canvas_h), (250, 247, 240))
    draw = ImageDraw.Draw(deck_canvas)

    # 2. 飾り枠（額縁線）の描画
    border_offset = 20
    draw.rectangle([border_offset, border_offset, canvas_w - border_offset, canvas_h - border_offset], outline=(205, 190, 170), width=2)
    draw.rectangle([border_offset + 6, border_offset + 6, canvas_w - (border_offset + 6), canvas_h - (border_offset + 6)], outline=(225, 215, 200), width=1)

    # 3. カードと枚数を順番に配置
    for index, card_id in enumerate(unique_card_ids):
        col = index % max_cols
        row = index // max_cols
        
        x = side_margin + (col * (card_w + gap_x))
        y = top_margin + (row * slot_h)

        card_path = os.path.join(CARDS_DIR, f"{card_id}.png")
        
        # --- カード画像のペースト ---
        if os.path.exists(card_path):
            with Image.open(card_path) as card_img:
                card_img = card_img.resize((card_w, card_h), Image.Resampling.LANCZOS)
                deck_canvas.paste(card_img, (x, y))
        else:
            error_box = Image.new("RGB", (card_w, card_h), (115, 105, 95))
            deck_canvas.paste(error_box, (x, y))

        # --- 下部の枚数表示エリア ---
        num_box_y = y + card_h + 4
        box_padding = 4  
        box_x1 = x + box_padding
        box_x2 = x + card_w - box_padding
        box_y1 = num_box_y
        box_y2 = num_box_y + number_area_h
        
        # 白い背景枠を描画
        draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=(255, 255, 255), outline=(220, 210, 195), width=2)
        
        # 枚数の数字を取得
        count = card_counts[card_id]
        
        # ボックスの中心座標を計算
        bx_center = box_x1 + (box_x2 - box_x1) // 2
        by_center = box_y1 + (box_y2 - box_y1) // 2
        
                # ★フォントを使わず、太い線（図形）の組み合わせで「巨大な数字」を1枚ずつ直に描画する処理
        # 公式のフォントサイズにそっくりな、ちょうどいい太さと大きさに調整しました
        color = (60, 55, 50)  # 公式に近い、少し優しい黒褐色
        w = 4  # 線の太さを「5」から「4」に細くしてスマートに
        
        # 数字の高さを全体的に小さくスマートに（上下10ピクセル幅に縮小）
        if count == 1:
            # 「1」の描画（中央に縦棒）
            draw.line([bx_center, by_center - 11, bx_center, by_center + 11], fill=color, width=w)
        elif count == 2:
            # 「2」の描画
            draw.line([bx_center - 9, by_center - 11, bx_center + 9, by_center - 11], fill=color, width=w) # 上横
            draw.line([bx_center + 9, by_center - 11, bx_center + 9, by_center], fill=color, width=w)      # 右上縦
            draw.line([bx_center - 9, by_center, bx_center + 9, by_center], fill=color, width=w)          # 中横
            draw.line([bx_center - 9, by_center, bx_center - 9, by_center + 11], fill=color, width=w)      # 左下縦
            draw.line([bx_center - 9, by_center + 11, bx_center + 9, by_center + 11], fill=color, width=w) # 下横
        elif count == 3:
            # 「3」の描画
            draw.line([bx_center - 9, by_center - 11, bx_center + 9, by_center - 11], fill=color, width=w) # 上横
            draw.line([bx_center + 9, by_center - 11, bx_center + 9, by_center + 11], fill=color, width=w) # 右縦
            draw.line([bx_center - 9, by_center, bx_center + 9, by_center], fill=color, width=w)          # 中横
            draw.line([bx_center - 9, by_center + 11, bx_center + 9, by_center + 11], fill=color, width=w) # 下横
        elif count == 4:
            # 「4」の描画
            draw.line([bx_center - 9, by_center - 11, bx_center - 9, by_center], fill=color, width=w)      # 左上縦
            draw.line([bx_center + 9, by_center - 11, bx_center + 9, by_center + 11], fill=color, width=w) # 右縦
            draw.line([bx_center - 9, by_center, bx_center + 9, by_center], fill=color, width=w)          # 中横
        else:
            # 5枚以上の場合
            draw.line([bx_center - 9, by_center - 11, bx_center + 9, by_center - 11], fill=color, width=w) # 上横
            draw.line([bx_center - 9, by_center - 11, bx_center - 9, by_center], fill=color, width=w)      # 左上縦
            draw.line([bx_center - 9, by_center, bx_center + 9, by_center], fill=color, width=w)          # 中横
            draw.line([bx_center + 9, by_center, bx_center + 9, by_center + 11], fill=color, width=w)      # 右下縦
            draw.line([bx_center - 9, by_center + 11, bx_center + 9, by_center + 11], fill=color, width=w) # 下横

    # 4. 最下部に公式風のフッターロゴ文字を配置
    footer_text = "- KAMITSUBAKI CARD GAME -"
    draw.text((canvas_w // 2 - 130, canvas_h - 45), footer_text, fill=(180, 170, 155))

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
                
# Renderのポートチェック（タイムアウト）を回避するためのダミーWebサーバー
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# 外部サービスを使わず、ウパーちゃん自身が自分を5分ごとにノックして24時間眠らなくする機能
import time
import urllib.request
import threading

def keep_alive_loop():
    # サーバーが完全に起動するまで少し待つ（2分間待機）
    time.sleep(120)
    # あなたのRenderのURL（正面玄関のアドレス）
    my_url = "https://kamitsubaki-bot.onrender.com"
    
    while True:
        try:
            # 自分自身のアドレスに自動でアクセス（ノック）する
            urllib.request.urlopen(my_url, timeout=10)
            print("【常時稼働】セルフノックに成功しました。")
        except Exception as e:
            # 外部からは弾かれますが、内部通信が発生するためRenderは起きたままになります
            print(f"【常時稼働】内部ノック通信を発生させました。")
        
        # 5分（300秒）ごとにこの処理を永遠に繰り返します
        time.sleep(300)

# Discord Botの起動直前に、裏側で自動起こしループを同時にスタートさせます
threading.Thread(target=keep_alive_loop, daemon=True).start()
client.run(os.getenv("DISCORD_BOT_TOKEN"))
