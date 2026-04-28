#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "======================================"
echo " シーディングトレーニングアプリ 起動"
echo "======================================"

# .env setup
if [ ! -f ".env" ]; then
  if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" > .env
  else
    echo ""
    read -p "ANTHROPIC_API_KEY を入力してください: " api_key
    echo "ANTHROPIC_API_KEY=$api_key" > .env
  fi
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  echo "SECRET_KEY=$SECRET" >> .env
  echo "✅ .env を作成しました"
fi

# Install dependencies
echo "依存パッケージを確認中..."
pip3 install -q -r requirements.txt

# Init DB
if [ ! -f "training_app.db" ]; then
  echo "データベースを初期化中..."
  python3 init_db.py
fi

echo ""
echo "✅ http://localhost:8000 で起動します"
echo "   管理者: admin@example.com / admin123"
echo "   テスト: tanaka@example.com / test123"
echo ""

uvicorn app:app --reload --host 0.0.0.0 --port 8000
