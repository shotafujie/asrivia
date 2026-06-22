"""pytest 共通設定: プロジェクトルートを import パスに追加する。

`tests/` には `__init__.py` が無いため、pytest の prepend import モードでは
`tests/` だけが sys.path に入り、`asr` / `audio2wav` / `main` を直接 import できない。
ルートに本ファイルを置くことでプロジェクトルートが import パスに乗る。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
