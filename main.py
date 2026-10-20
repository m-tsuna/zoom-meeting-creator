"""
Zoom 会議作成プログラム（課題4：Zoom API）

会議名・開始日時・長さを入力すると、Zoom に会議を予約して、
会議ID・パスワード・参加リンクを表示します。

処理の流れ：
  1. .env から Zoom の鍵（Account ID・Client ID・Client Secret）を読む
  2. 鍵を Zoom に送り、1時間有効の「通行証（アクセストークン）」をもらう
  3. 会議名・開始日時・長さを入力してもらう
  4. 通行証を見せて、会議の作成を Zoom に頼む
  5. 返ってきた会議ID・パスワード・参加リンクを表示する
"""

import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

# ===== 設定（ここを変えれば動きを変えられます） =====

# 鍵を書いておくファイル（main.py と同じフォルダに置く）
ENV_FILE = Path(__file__).resolve().parent / ".env"

# 通行証（アクセストークン）をもらう場所
TOKEN_URL = "https://zoom.us/oauth/token"

# 会議を作る場所（users/me は「自分のアカウント」という意味）
CREATE_MEETING_URL = "https://api.zoom.us/v2/users/me/meetings"

# 会議の時刻は日本時間で扱う
TIMEZONE = "Asia/Tokyo"

# 入力の決まり
DEFAULT_TOPIC = "Zoom会議"  # 会議名が空欄のとき
DEFAULT_DURATION = 40  # 長さが空欄のとき（無料アカウントは40分で切れる）
FREE_LIMIT_MINUTES = 40  # これを超えたら注意を出す
MAX_DURATION = 1440  # 長さの上限（24時間）
DATETIME_FORMAT = "%Y-%m-%d %H:%M"  # 開始日時の入力の形（例：2026-10-21 10:00）

# 通信を待つ最長の秒数
TIMEOUT_SECONDS = 30

# Zoom App Marketplace（エラーの案内に使う）
MARKETPLACE_URL = "https://marketplace.zoom.us/"


class ZoomError(Exception):
    """利用者に見せるエラー。メッセージを表示してプログラムを終了する。"""


# ===== 1. 鍵の読み込み =====


def load_credentials():
    """.env から Zoom の鍵を3つ読み、(account_id, client_id, client_secret) を返す。"""
    if not ENV_FILE.exists():
        raise ZoomError(
            f".env が見つかりません（探した場所：{ENV_FILE}）。\n"
            ".env.example をコピーして名前を .env に変え、Zoom の鍵を書き込んでください。"
        )

    load_dotenv(ENV_FILE)
    names = ["ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET"]
    values = [os.getenv(name, "").strip() for name in names]

    empty = [name for name, value in zip(names, values) if not value]
    if empty:
        raise ZoomError(
            f".env に値が入っていません：{', '.join(empty)}\n"
            f"{MARKETPLACE_URL} で作ったアプリの「App Credentials」の値を貼り付けてください。"
        )
    return values


# ===== 2. 通行証（アクセストークン）の取得 =====


def get_access_token(account_id, client_id, client_secret):
    """鍵を Zoom に送り、1時間有効のアクセストークンを受け取って返す。"""
    try:
        response = requests.post(
            TOKEN_URL,
            params={"grant_type": "account_credentials", "account_id": account_id},
            auth=(client_id, client_secret),  # Client ID と Secret は Basic 認証で送る
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException:
        raise ZoomError("Zoom につながりませんでした。インターネットの接続を確認してください。")

    if response.ok:
        return response.json()["access_token"]

    # 失敗したときは、Zoom が返す理由（reason）を見て案内を変える
    data = safe_json(response)
    error = data.get("error", "")
    reason = data.get("reason", response.text)
    if error == "invalid_client":
        hint = "Client ID か Client Secret が間違っています。「App Credentials」の値を貼り直してください。"
    elif "account" in reason.lower():
        hint = "Account ID が間違っています。「App Credentials」の値を貼り直してください。"
    else:
        hint = "アプリが有効になっているか（「Activation」で Activate したか）を確認してください。"
    raise ZoomError(
        f"Zoom の通行証（アクセストークン）をもらえませんでした。\n"
        f"{hint}\n（Zoom からの返事：{response.status_code} {reason}）"
    )


# ===== 3. 会議情報の入力 =====


def ask_topic():
    """会議名を聞く。空欄なら既定の名前にする。"""
    topic = input(f"会議名（空欄なら「{DEFAULT_TOPIC}」）: ").strip()
    return topic or DEFAULT_TOPIC


def ask_start_time():
    """開始日時を聞き、正しい形の未来の日時になるまで聞き直す。datetime を返す。"""
    while True:
        text = input("開始日時（例：2026-10-21 10:00）: ")
        # 全角の数字や記号（２０２６－１０…）も半角にそろえ、前後の空白を取る
        text = unicodedata.normalize("NFKC", text).strip()
        if not text:
            print("  開始日時を入力してください。")
            continue
        try:
            start = datetime.strptime(text, DATETIME_FORMAT)
        except ValueError:
            print("  形が違います。「2026-10-21 10:00」のように、年-月-日 時:分 で入力してください。")
            continue
        now = datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)
        if start <= now:
            print("  過去の日時です。これから先の日時を入力してください。")
            continue
        return start


def ask_duration():
    """長さ（分）を聞き、1〜上限の整数になるまで聞き直す。空欄なら既定の分数にする。"""
    while True:
        text = input(f"長さ（分。空欄なら{DEFAULT_DURATION}）: ")
        text = unicodedata.normalize("NFKC", text).strip()
        if not text:
            return DEFAULT_DURATION
        if not text.isdigit() or not 1 <= int(text) <= MAX_DURATION:
            print(f"  1〜{MAX_DURATION} の数字（分）で入力してください。")
            continue
        duration = int(text)
        if duration > FREE_LIMIT_MINUTES:
            print(f"  注意：無料アカウントでは、会議は{FREE_LIMIT_MINUTES}分で切れます。")
        return duration


# ===== 4. 会議の作成 =====


def create_meeting(token, topic, start, duration):
    """日時を指定した会議（予約会議）を作り、Zoom から返ってきた会議の情報を返す。"""
    body = {
        "topic": topic,
        "type": 2,  # 2 = 日時を指定した会議（1 は今すぐの会議、8 は定期的な会議）
        "start_time": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "timezone": TIMEZONE,
        "duration": duration,
        # パスワードは指定しない → Zoom がランダムな値を作る
    }
    try:
        response = requests.post(
            CREATE_MEETING_URL,
            headers={"Authorization": f"Bearer {token}"},  # 通行証を見せる
            json=body,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException:
        raise ZoomError("Zoom につながりませんでした。インターネットの接続を確認してください。")

    if response.ok:
        return response.json()

    data = safe_json(response)
    code = data.get("code")
    message = data.get("message", response.text)
    if code == 4711:  # 通行証に必要な許可（スコープ）が入っていない
        hint = "アプリの「Scopes」に meeting:write:meeting:admin を追加してください。"
    elif response.status_code == 429:
        hint = "短い時間に何度も実行したため、Zoom に止められました。しばらく待ってから実行してください。"
    else:
        hint = "下の Zoom からの返事を確認してください。"
    raise ZoomError(
        f"会議を作成できませんでした。\n{hint}\n"
        f"（Zoom からの返事：{response.status_code} {message}）"
    )


# ===== 5. 結果の表示 =====


def format_meeting_id(meeting_id):
    """会議IDを Zoom アプリと同じ形に区切る（例：81234567890 → 812 3456 7890）。"""
    digits = str(meeting_id)
    if len(digits) == 11:
        return f"{digits[:3]} {digits[3:7]} {digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    return digits


def show_meeting(meeting, start, duration):
    """会議の情報を表示する。主催者用の開始リンク（start_url）は、悪用を防ぐため表示しない。"""
    print()
    print("会議を作成しました。")
    print(f"会議名    : {meeting['topic']}")
    print(f"開始日時  : {start.strftime(DATETIME_FORMAT)}（日本時間）")
    print(f"長さ      : {duration}分")
    print(f"会議ID    : {format_meeting_id(meeting['id'])}")
    print(f"パスワード: {meeting.get('password', '（なし）')}")
    print(f"参加リンク: {meeting['join_url']}")


# ===== 共通の部品 =====


def safe_json(response):
    """Zoom の返事を JSON として読む。JSON でなければ空の辞書を返す。"""
    try:
        return response.json()
    except ValueError:
        return {}


def main():
    try:
        account_id, client_id, client_secret = load_credentials()
        token = get_access_token(account_id, client_id, client_secret)
        topic = ask_topic()
        start = ask_start_time()
        duration = ask_duration()
        meeting = create_meeting(token, topic, start, duration)
        show_meeting(meeting, start, duration)
    except ZoomError as error:
        print(f"エラー：{error}")
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        # Ctrl + C で止めたとき、または入力が途中で終わったとき
        print("\n中断しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()
