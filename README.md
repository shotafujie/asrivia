# asrivia

## できること
- ローカルで文字起こしができます．
- PiP(Picture-in-Picture)に対応しているので，常に最前面表示で，アプリの上にも重ねて表示することができます．
- モデルは開発時点で最高の文字起こし精度，速度で機能するwhisper-large-v3-turboを使っています．mlx-whisperなのでMacで動かすことを前提にしています．
- 日本語-英語間で翻訳ができます．Plamoを使っています．開発者の環境(M4Max, 128GB)では4秒ほどのラグがあります．
- **ASRバックエンドの選択が可能になりました**：ローカル（mlx）またはOpenAI APIを選択できます．

## 使い方

### 基本的な使い方

```bash
python3 main.py --language {ja|en|auto}
```

- `--language`: 認識言語モードを指定します
  - `ja`: 日本語のみ（デフォルト）
  - `en`: 英語のみ
  - `auto`: 自動判定

### 翻訳機能

```bash
python3 main.py --language {ja|en|auto} --translate
```

- `--translate`: 翻訳を有効にします（デフォルトは翻訳無し）
  - 日本語→英語、英語→日本語の翻訳が可能です

### ASRバックエンドの選択

```bash
python3 main.py --backend {mlx|openai}
```

- `--backend`: ASRバックエンドを指定します
  - `mlx`: ローカルでmlx-whisperを使用（デフォルト）
    - Macでの動作に最適化されています
    - インターネット接続不要
  - `openai`: OpenAI Whisper APIを使用
    - 環境変数 `OPENAI_API_KEY` の設定が必要です
    - インターネット接続が必要です
    - `pip install openai` で事前にパッケージをインストールしてください

### モデルの指定

```bash
python3 main.py --model {モデル名}
```

- `--model`: 使用するモデルを指定します
  - mlxバックエンドの場合:
    - デフォルト: `mlx-community/whisper-large-v3-turbo`
    - Hugging Faceリポジトリパスを指定します
    - 例: `mlx-community/whisper-large-v3`, `mlx-community/whisper-medium`
  - openaiバックエンドの場合:
    - デフォルト: `whisper-1`
    - OpenAIのモデル名を指定します

### 使用例

```bash
# ローカルで日本語音声認識（デフォルト設定）
python3 main.py

# 自動言語判定で翻訳付き
python3 main.py --language auto --translate

# OpenAI APIを使用して英語音声認識
python3 main.py --backend openai --language en

# 特定のmlxモデルを使用
python3 main.py --backend mlx --model mlx-community/whisper-medium

# OpenAI APIで全機能を使用
python3 main.py --backend openai --language auto --translate
```

## 注意事項

- OpenAI APIを使用する場合は、環境変数 `OPENAI_API_KEY` を設定する必要があります
- OpenAI APIを使用する場合は、`pip install openai` でopenaiパッケージをインストールしてください
- mlxバックエンドはMac（Apple Silicon）で最適に動作します
