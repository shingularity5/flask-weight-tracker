# app.py - 体重管理Webアプリのバックエンド

from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import datetime

# データベースファイルのパスを定義
DATABASE = 'weight_tracker.db'

# データベースの初期化関数
# アプリケーション起動時にテーブルが存在しない場合は作成する
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT, -- 自動で増えるID
                date TEXT NOT NULL UNIQUE,            -- 日付 (例: 'YYYY-MM-DD') - ユニーク制約で重複を防止
                weight REAL NOT NULL,                 -- 体重 (小数点数)
                memo TEXT                             -- メモ (任意)
            )
        ''')
        conn.commit() # 変更を保存

# データベース接続を取得するヘルパー関数
# 取得した行を辞書のようにカラム名でアクセスできるようにする (sqlite3.Row)
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # これにより、行を辞書形式で取得できる
    return conn

# Flaskアプリケーションの初期化
app = Flask(__name__)

# --- ルーティングとビュー関数 ---

# 一覧画面 (HOME) のルート
@app.route('/')
def index():
    conn = get_db()
    # dailyテーブルから全ての日次データを日付の昇順で取得
    dailies = conn.execute('SELECT * FROM daily ORDER BY date ASC').fetchall()
    conn.close() # データベース接続を閉じる

    # ここを修正: sqlite3.Row オブジェクトを通常の辞書に変換
    # Jinja2の tojson フィルターが sqlite3.Row を直接シリアライズできないため
    dailies_as_dicts = [dict(daily) for daily in dailies]

    # グラフ描画用にデータを整形
    # 日付、体重、メモのリストをそれぞれ作成
    dates = [d['date'] for d in dailies_as_dicts] # 変換後のデータを使用
    weights = [d['weight'] for d in dailies_as_dicts] # 変換後のデータを使用
    memos = [d['memo'] if d['memo'] else '' for d in dailies_as_dicts] # 変換後のデータを使用

    # index.htmlテンプレートをレンダリングし、整形したデータを渡す
    # dailies_as_dicts をテンプレートに渡す
    return render_template('index.html', dates=dates, weights=weights, memos=memos, dailies=dailies_as_dicts)

# 入力画面のルート
@app.route('/input', methods=['GET', 'POST'])
def input_daily():
    # POSTリクエスト (フォームが送信された場合) の処理
    if request.method == 'POST':
        date = request.form['date']
        weight = request.form['weight']
        memo = request.form.get('memo', '') # メモは任意なので、値がない場合は空文字列を設定

        conn = get_db()
        try:
            # データベースに新しいdailyデータを挿入
            conn.execute('INSERT INTO daily (date, weight, memo) VALUES (?, ?, ?)',
                         (date, weight, memo))
            conn.commit() # 変更を保存
            return redirect(url_for('index')) # 登録後、一覧画面にリダイレクト
        except sqlite3.IntegrityError:
            # 日付が重複した場合 (UNIQUE制約違反) のエラー処理
            error_message = "その日付は既に登録されています。修正する場合は一覧から選択してください。"
            # エラーメッセージと入力された値を保持して入力画面を再表示
            return render_template('input.html', error=error_message,
                                   default_date=date, default_weight=weight, default_memo=memo)
        finally:
            conn.close() # データベース接続を閉じる
    
    # GETリクエスト (初めてページにアクセスした場合) の処理
    # デフォルトの日付として今日の日付を設定
    default_date = datetime.date.today().isoformat()
    return render_template('input.html', default_date=default_date)

# 登録画面 (修正) のルート
# <int:daily_id> でURLからdailyのIDを受け取る
@app.route('/edit/<int:daily_id>', methods=['GET', 'POST'])
def edit_daily(daily_id):
    conn = get_db()
    # 渡されたIDに対応するdailyデータをデータベースから取得
    daily = conn.execute('SELECT * FROM daily WHERE id = ?', (daily_id,)).fetchone()

    # データが見つからない場合 (例: 不正なIDでアクセスした場合)
    if daily is None:
        conn.close()
        return "Daily not found", 404 # 404エラーを返す

    # POSTリクエスト (フォームが送信された場合) の処理
    if request.method == 'POST':
        new_date = request.form['date']
        new_weight = request.form['weight']
        new_memo = request.form.get('memo', '')

        try:
            # データベースのdailyデータを更新
            conn.execute('UPDATE daily SET date = ?, weight = ?, memo = ? WHERE id = ?',
                         (new_date, new_weight, new_memo, daily_id))
            conn.commit() # 変更を保存
            return redirect(url_for('index')) # 更新後、一覧画面にリダイレクト
        except sqlite3.IntegrityError:
            # 更新後の日付が重複した場合のエラー処理
            error_message = "その日付は既に登録されています。"
            # エラーメッセージと元々のdailyデータを保持して修正画面を再表示
            return render_template('edit.html', daily=daily, error=error_message,
                                   default_date=new_date, default_weight=new_weight, default_memo=new_memo)
        finally:
            conn.close() # データベース接続を閉じる
    
    # GETリクエスト (初めてページにアクセスした場合) の処理
    conn.close()
    # 取得したdailyデータをedit.htmlテンプレートに渡してレンダリング
    return render_template('edit.html', daily=daily)

# アプリケーションのエントリーポイント
# このスクリプトが直接実行された場合にのみ以下のコードが実行される
if __name__ == '__main__':
    init_db() # アプリケーション起動時にデータベースを初期化 (初回のみテーブル作成)
    app.run(debug=True) # Flask開発サーバーをデバッグモードで起動