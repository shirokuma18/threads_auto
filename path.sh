# コメント行と空行を除いて .env を読み込み
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi
source ./venv/bin/activate
