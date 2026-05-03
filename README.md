# asrivia

ローカルで動作する音声認識・翻訳アプリケーション。Whisperを使用したリアルタイム文字起こしと、日本語-英語間の翻訳機能を提供します。

## 主な機能

- **リアルタイム音声認識**: Whisperによる高精度な文字起こし
- **PiPウィンドウ表示**: 常に最前面に表示され、他のアプリケーションの上に重ねて使用可能
- **日英翻訳**: Opus-MT（軽量・高速）またはTranslateGemma（高品質）を選択可能
- **非同期翻訳パイプライン**: 認識を待たせず翻訳を別スレッドで実行（バックプレッシャー制御つき）
- **複数ASRバックエンド対応**: MLX / PyTorch（openai） / stable-ts（VAD付き） / HuggingFace（バイアシング対応）
- **コンテキストバイアシング**: 専門用語や固有名詞をブースト（HFバックエンドのみ、`words.json`で管理）
- **入力デバイス選択**: PiPウィンドウからマイク等の入力デバイスを切り替え可能
- **辞書登録UI**: 認識結果のOOV（未知語）候補からワンクリックで辞書追加
- **言語自動判定**: 日本語/英語を自動で判別
- **動的セグメンテーション**: 発話終了を自動検知して即座に認識処理を開始（低遅延モード）

## 前提条件

### ハードウェア要件

| バックエンド | 対応環境 | 推奨メモリ |
|-------------|---------|-----------|
| MLX | macOS（Apple Silicon） | 16GB以上 |
| PyTorch（openai） | macOS / Linux / Windows | 16GB以上 |
| stable-ts | macOS / Linux / Windows | 16GB以上 |
| HuggingFace（hf） | macOS / Linux / Windows（GPUあれば高速） | 16GB以上 |

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

#### stable-tsバックエンド用

```bash
pip install stable-ts pyaudio
```

#### hfバックエンド用（HuggingFace Whisper + バイアシング）

```bash
pip install transformers torch pyaudio
```

初回実行時に、Whisperモデルが自動的にダウンロードされます。

### 翻訳機能を使用する場合

翻訳器は2種類から選べます。デフォルトは軽量CPU向けの **Opus-MT**、高品質を求めるなら **TranslateGemma**（GPU推奨）。

```bash
# Opus-MT / TranslateGemma 共通: transformers と torch
pip install transformers torch sentencepiece
```

`uv sync` を使う場合は不要です（`pyproject.toml` に含まれています）。

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
python main.py --language {ja|en|auto} --translate [--translator {opus|gemma}]
```

- `--translate`: 翻訳を有効化（日本語↔英語）
- `--translator`: 翻訳器を指定
  - `opus`: Opus-MT（デフォルト、軽量・高速、CPUでも実用）
  - `gemma`: TranslateGemma 4B（高品質、GPU推奨）

翻訳は別スレッドで非同期実行されます。認識テキストは即座にPiPに表示され、翻訳は完了次第追記されます。翻訳ジョブが詰まった場合は古いジョブを破棄し、最新の発話を優先します。

### ASRバックエンドの選択

```bash
python main.py --backend {mlx|openai|stable-ts|hf}
```

- `--backend`: ASRバックエンドを指定
  - `mlx`: mlx-whisperを使用（デフォルト、Mac最適化）
  - `openai`: PyTorch版Whisperを使用（クロスプラットフォーム）
  - `stable-ts`: Whisper + Silero VAD（ハルシネーション抑制）
  - `hf`: HuggingFace Whisper + コンテキストバイアシング（専門用語をブースト）

### コンテキストバイアシング（hfバックエンド）

頻出する専門用語・固有名詞をリポジトリ直下の `words.json` に登録すると、認識時にそれらの単語が出やすくなります。

```json
[
  {"word": "Agile", "boost": 2.0, "note": ""},
  {"word": "Kubernetes", "boost": 2.5, "note": "infra"}
]
```

- `boost`: 大きいほど強く優先（目安: 1.5〜3.0）
- ファイルは `mtime` を監視して自動リロードされます
- PiPウィンドウの `📚` ボタンから登録UIも開けます

### 辞書登録UIのみ起動

ASRを動かさず、辞書管理だけしたい場合:

```bash
python main.py --dict
```

OOV候補リストや既存エントリの編集が可能です。

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
  - stable-tsバックエンド: Whisperモデル名（openaiと同じ）
    - デフォルト: `large-v3-turbo`
  - hfバックエンド: HuggingFaceモデルID
    - デフォルト: `openai/whisper-large-v3-turbo`

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

# 自動言語判定で翻訳付き（Opus-MT、軽量）
python main.py --language auto --translate

# TranslateGemmaで高品質翻訳（GPU推奨）
python main.py --language auto --translate --translator gemma

# 動的VAD + 翻訳
python main.py --dynamic-vad --language auto --translate

# PyTorch版Whisperを使用して英語音声認識
python main.py --backend openai --language en

# stable-tsでハルシネーション抑制
python main.py --backend stable-ts --dynamic-vad

# HFバックエンド + バイアシング（words.json必須）
python main.py --backend hf --dynamic-vad

# 特定のmlxモデルを使用
python main.py --backend mlx --model mlx-community/whisper-medium

# 辞書登録UIのみ起動
python main.py --dict
```

<img width="495" height="140" alt="image" src="https://github.com/user-attachments/assets/443a3a83-f6b5-422d-80b5-80d786ffe380" />

<img width="501" height="152" alt="image" src="https://github.com/user-attachments/assets/fa9ef46b-4576-47a2-8189-14bbe9dd9c47" />

## PiPウィンドウの操作

- ウィンドウは常に最前面に表示されます
- `＋`/`－`ボタンでフォントサイズを調整可能（8〜96pt）
- 入力デバイスのプルダウンからマイク等を切り替え可能
- `📚` ボタンで辞書登録ウィンドウを開く（hfバックエンド時のみ表示）
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

- `transformers` と `torch` がインストールされているか確認してください
- TranslateGemma（`--translator gemma`）はGPU/MPSがないと処理時間が大きくなります。CPU運用なら `opus`（デフォルト）推奨
- 初回実行時はモデルのダウンロードに時間がかかります

### バイアシングが効かない（hfバックエンド）

- `words.json` がリポジトリ直下に存在し、有効なJSON配列になっているか確認
- `boost` 値が小さすぎる可能性があります（1.5以上を試してください）

## 制限事項

- mlxバックエンドはApple Silicon Mac専用です
- TranslateGemmaはローカルで動作するため、マシンスペックによって処理時間が変わります（M4 Max, 128GBで数秒のラグ）
- 通常モードでは3秒ごとに音声を認識するため、リアルタイム性には若干の遅延があります（`--dynamic-vad`で軽減可能）
- コンテキストバイアシングはhfバックエンドのみで有効です

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
