# zoom-meeting-creator

Zoom API を使って、日時を指定した Zoom 会議を作成し、**会議ID・パスワード・参加リンク**を表示する Python プログラムです。
（AIエンジニア講座 課題4：Zoom API）

## 何をするものか

```
会議名（空欄なら「Zoom会議」）: 課題の打ち合わせ
開始日時（例：2026-10-21 10:00）: 2026-10-21 10:00
長さ（分。空欄なら40）:

会議を作成しました。
会議名    : 課題の打ち合わせ
開始日時  : 2026-10-21 10:00（日本時間）
長さ      : 40分
会議ID    : 812 3456 7890
パスワード: abc123
参加リンク: https://us05web.zoom.us/j/81234567890?pwd=xxxx
```

- 認証は Zoom の **Server-to-Server OAuth**（ブラウザでのログインは不要）
- パスワードは Zoom が自動で作ります
- 主催者用の開始リンク（`start_url`）は、悪用を防ぐため表示しません

## 事前準備

1. Python 3 と、次のライブラリ（Anaconda には最初から入っています）

   ```
   pip install requests python-dotenv
   ```

2. Zoom のアカウント（無料でも使えます。ただし無料の会議は40分で切れます）

## 秘密ファイル（.env）の用意の仕方

1. [Zoom App Marketplace](https://marketplace.zoom.us/) にログインし、「Develop」→「Build App」→「Server-to-Server OAuth App」でアプリを作る
2. 「Information」で会社名（個人名でよい）・連絡先の名前とメールを入れる
3. 「Scopes」で次の2つを追加する
   - `meeting:write:meeting:admin`（会議を作る）
   - `meeting:read:meeting:admin`（作った会議を読む。動作確認用）
4. 「Activation」で「Activate your app」を押す
5. `.env.example` をコピーして名前を `.env` にし、「App Credentials」の3つの値を書き込む

   ```
   ZOOM_ACCOUNT_ID=...
   ZOOM_CLIENT_ID=...
   ZOOM_CLIENT_SECRET=...
   ```

`.env` は鍵そのものなので、GitHub には載せません（`.gitignore` に入れています）。

## 使い方

```
python main.py
```

会議名・開始日時（日本時間）・長さ（分）を入力すると、会議が作られます。

## ファイル

| ファイル | 内容 |
|---|---|
| `main.py` | プログラム本体 |
| `.env.example` | `.env` の書き方の見本 |
| `要件定義書.md` | 何をどう作るかを決めた文書（方式を選んだ理由もここ） |
