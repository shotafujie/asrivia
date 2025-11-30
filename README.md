# asrivia

## できること

- ローカルで文字起こしができます．
- PiP(Picture-in-Picture)に対応しているので，常に最前面表示で，アプリの上にも重ねて表示することができます．
- モデルは開発時点で最高の文字起こし精度，速度で機能するwhisper-large-v3-turboを使っています．mlx-whisperなのでMacで動かすことを前提にしています．
- 日本語-英語間で翻訳ができます．Plamoを使っています．開発者の環境(M4Max, 128GB)では4秒ほどのラグがあります．
- **ASRバックエンドの選択が可能になりました**：ローカル（mlx）またはローカルPyTorch版Whisperを選択できます．

## セットアップ

### mlxバックエンド用

```bash
pip install mlx-whisper
```

### openaiバックエンド用（ローカルPyTorch版Whisper）

```bash
# Whisperライブラリのインストール
pip install openai-whisper

# PyTorchのインストール
pip install torch

# ffmpegのインストール（macOS）
brew install ffmpeg

# ffmpegのインストール（Ubuntu/Debian）
# sudo apt update && sudo apt install ffmpeg

# ffmpegのインストール（Windows）
# choco install ffmpeg
```

初回実行時に、Whisperモデルが自動的にダウンロードされます。

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
  - 日本語→英語、英語→日語の翻訳が可能です

### ASRバックエンドの選択

```bash
python3 main.py --backend {mlx|openai}
```

- `--backend`: ASRバックエンドを指定します
  - `mlx`: ローカルでmlx-whisperを使用（デフォルト）
    - Macでの動作に最適化されています
    - インターネット接続不要
  - `openai`: ローカルPyTorch版Whisperライブラリを使用
    - インターネット接続不要（初回モデルダウンロード時のみ必要）
    - クロスプラットフォーム対応（Mac/Linux/Windows）

### モデルの指定

```bash
python3 main.py --model {モデル名}
```

- `--model`: 使用するモデルを指定します
  - mlxバックエンドの場合:
    - デフォルト: `mlx-community/whisper-large-v3-turbo`
    - Hugging Faceリポジトリパスを指定します
    - 例: `mlx-community/whisper-large-v3`, `mlx-community/whisper-medium`
  - openaiバックエンド（ローカルPyTorch版Whisper）の場合:
    - デフォルト: `large-v3-turbo`
    - 利用可能なモデル: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`, `large-v3-turbo`

### 使用例

```bash
# ローカルで日本語音声認識（デフォルト設定）
python3 main.py

# 自動言語判定で翻訳付き
python3 main.py --language auto --translate

# PyTorch版Whisperを使用して英語音声認識
python3 main.py --backend openai --language en

# 特定のmlxモデルを使用
python3 main.py --backend mlx --model mlx-community/whisper-medium

# PyTorch版Whisperで全機能を使用
python3 main.py --backend openai --language auto --translate

# PyTorch版Whisperで特定のモデルを使用
python3 main.py --backend openai --model medium
```

<img width="495" height="140" alt="image" src="https://github.com/user-attachments/assets/443a3a83-f6b5-422d-80b5-80d786ffe380" />

<img width="501" height="152" alt="image" src="https://github.com/user-attachments/assets/fa9ef46b-4576-47a2-8189-14bbe9dd9c47" />

## 注意事項

- mlxバックエンドはMac（Apple Silicon）で最適に動作します
- openaiバックエンド（PyTorch版Whisper）はクロスプラットフォームで動作します

---

## Support

このリポジトリが役に立った/気に入っていただけたら，以下のいずれかの形でサポートしていただけると嬉しいです🙌

- GitHubでのStar⭐
- SNS等でのシェア・紹介
- Buy Me a Coffeeからのご支援

If you find this project useful, you can support it in any of the following ways 🙌

- Give the repository a ⭐️ on GitHub
- Share it on social media or with your friends
- Support me on Buy Me a Coffee

<a href="https://buymeacoffee.com/fujiemon" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee">
</a>
