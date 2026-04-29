#!/bin/bash
cd "$(dirname "$0")"
echo "📦 ライブラリをインストール中..."
pip3 install -r requirements.txt -q
echo "🚀 アプリを起動します → http://localhost:5001"
python app.py
