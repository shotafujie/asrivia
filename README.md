# asrivia

ローカルで動作する音声認識・翻訳アプリケーション。Whisperを使用したリアルタイム文字起こしと、日本語-英語間の翻訳機能を提供します。

## 主な機能

- **リアルタイム音声認識**: Whisperによる高精度な文字起こし
- **PiPウィンドウ表示**: 常に最前面に表示され、他のアプリケーションの上に重ねて使用可能
- **日英翻訳**: PLaMoを使用した日本語↔英語の翻訳
- **複数バックエンド対応**: MLX（Mac最適化）またはPyTorch版Whisperを選択可能
- **言語自動判定**: 日本語/英語を自動で判別
- **動的セグメンテーション**: 発話終了を自動検知して即座に認識処理を開始（低遅延モード）

## 前提条件

### ハードウェア要件

| バックエンド | 対応環境 | 推奨メモリ |
|-------------|---------|-----------|
| MLX | macOS（Apple Silicon） | 16GB以上 |
| PyTorch（openai） | macOS / Linux / Windows | 16GB以上 |

### ソフトウェア要件

- Python 3.9以上
- ffmpeg（openaiバックエンド使用時）

## セットアップ

### uvを使用する場合（推奨）

```bash
# 依存関係のインストール
uv sync

# 実行
uv run python main.py
```

### pipを使用する場合

#### mlxバックエンド用

```bash
pip install mlx-whisper pyaudio
```

#### openaiバックエンド用（ローカルPyTorch版Whisper）

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

### 翻訳機能を使用する場合

```bash
# PLaMo翻訳ツールのインストール
pip install plamo-translate
```

## 使い方

### 基本的な使い方

```bash
python main.py --language {ja|en|auto}
```

- `--language`: 認識言語モードを指定
  - `ja`: 日本語のみ（デフォルト）
  - `en`: 英語のみ
  - `auto`: 自動判定

### 翻訳機能

```bash
python main.py --language {ja|en|auto} --translate
```

- `--translate`: 翻訳を有効化
  - 日本語→英語、英語→日本語の翻訳が可能

### ASRバックエンドの選択

```bash
python main.py --backend {mlx|openai}
```

- `--backend`: ASRバックエンドを指定
  - `mlx`: mlx-whisperを使用（デフォルト、Mac最適化）
  - `openai`: PyTorch版Whisperを使用（クロスプラットフォーム）

### モデルの指定

```bash
python main.py --model {モデル名}
```

- `--model`: 使用するモデルを指定
  - mlxバックエンド: Hugging Faceリポジトリパス
    - デフォルト: `mlx-community/whisper-large-v3-turbo`
    - 例: `mlx-community/whisper-large-v3`, `mlx-community/whisper-medium`
  - openaiバックエンド: Whisperモデル名
    - デフォルト: `large-v3-turbo`
    - 利用可能: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`, `large-v3-turbo`

### 動的セグメンテーション（低遅延モード）

通常モードでは3秒ごとに音声を処理しますが、動的セグメンテーションを有効にすると、発話終了を自動検知して即座に認識処理を開始します。

```bash
python main.py --dynamic-vad
```

#### パラメータの調整

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--dynamic-vad` | 動的セグメンテーションを有効化 | 無効 |
| `--silence-threshold` | 無音判定閾値（小さいほど敏感） | 0.01 |
| `--silence-duration` | 発話終了と判定する無音継続時間（秒） | 0.5 |
| `--min-record` | 最小録音時間（秒） | 0.5 |
| `--max-record` | 最大録音時間（秒） | 5.0 |
| `--overlap` | 次のセグメントとのオーバーラップ時間（秒） | 0.0 |

```bash
# 動的VADを有効化（デフォルト設定）
python main.py --dynamic-vad

# 発話終了検知を早める（0.3秒の無音で終了判定）
python main.py --dynamic-vad --silence-duration 0.3

# オーバーラップを有効化して文脈の途切れを防ぐ
python main.py --dynamic-vad --overlap 0.5

# 全パラメータをカスタマイズ
python main.py --dynamic-vad --silence-threshold 0.02 --silence-duration 0.4 --min-record 0.3 --max-record 4.0 --overlap 0.3
```

### 使用例

```bash
# ローカルで日本語音声認識（デフォルト設定）
python main.py

# 動的VADで低遅延認識
python main.py --dynamic-vad

# 自動言語判定で翻訳付き
python main.py --language auto --translate

# 動的VAD + 翻訳
python main.py --dynamic-vad --language auto --translate

# PyTorch版Whisperを使用して英語音声認識
python main.py --backend openai --language en

# 特定のmlxモデルを使用
python main.py --backend mlx --model mlx-community/whisper-medium

# PyTorch版Whisperで全機能を使用
python main.py --backend openai --language auto --translate

# PyTorch版Whisperで特定のモデルを使用
python main.py --backend openai --model medium
```

<img width="495" height="140" alt="image" src="https://github.com/user-attachments/assets/443a3a83-f6b5-422d-80b5-80d786ffe380" />

<img width="501" height="152" alt="image" src="https://github.com/user-attachments/assets/fa9ef46b-4576-47a2-8189-14bbe9dd9c47" />

## PiPウィンドウの操作

- ウィンドウは常に最前面に表示されます
- `＋`/`－`ボタンでフォントサイズを調整可能（8〜32pt）
- ウィンドウを閉じるとアプリケーションが終了します

## トラブルシューティング

### 音声が認識されない

1. マイクの権限を確認してください（システム環境設定 → プライバシーとセキュリティ → マイク）
2. 正しい入力デバイスが選択されているか確認してください

### モデルのダウンロードに失敗する

- インターネット接続を確認してください
- 初回起動時はモデルのダウンロードに時間がかかります

### PyTorch版で「ffmpeg not found」エラー

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg
```

### 翻訳が動作しない

- `plamo-translate`がインストールされているか確認してください
- PLaMoが正しくセットアップされているか確認してください

## 制限事項

- mlxバックエンドはApple Silicon Mac専用です
- 翻訳機能（PLaMo）はローカルで動作するため、マシンスペックによって処理時間が変わります（M4 Max, 128GBで約4秒のラグ）
- 通常モードでは3秒ごとに音声を認識するため、リアルタイム性には若干の遅延があります（`--dynamic-vad`で軽減可能）

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
