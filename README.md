# asrivia

## できること

- ローカルで文字起こしができます．
- PiP(Picture-in-Picture)に対応しているので，常に最前面表示で，アプリの上にも重ねて表示することができます．
- モデルは開発時点で最高の文字起こし精度，速度で機能するwhisper-large-v3-turboを使っています．mlx-whisperなのでMacで動かすことを前提にしています．
- 日本語-英語間で翻訳ができます．Plamoを使っています．開発者の環境(M4Max, 128GB)では4秒ほどのラグがあります．

##  使い方

- `python3 main.py --language {ja|en|auto}`で起動します．
    - languageは日本語のみ，英語のみ，自動識別のモード切り替えができます．デフォルトは日本語です．
- `python3 main.py --language {ja|en|auto} (--translate)`で翻訳の有無を切り替えられます．デフォルトは翻訳無しです．
