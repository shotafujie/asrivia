# テスト設計: qwen バックエンドで辞書(words.json)を context として反映する

実モデルには依存させず、`mlx_qwen3_asr.Session` を偽物に差し替えて呼び出し引数と戻り値を観測する
(`tests/test_qwen_backend.py`)。

### SPEC-001 `registry_path` を指定しない場合、認識は context を空文字で呼ぶ

- **TC-001-1** registry_path 未指定で1回認識 → Session に渡る context が空文字

### SPEC-002 words.json に登録された語は、すべて認識時の context に含まれる

- **TC-002-1** words.json に2語(英字1・日本語1)登録 → context に両方の語が含まれる

### SPEC-003 context は登録語を登録順に `", "` で連結した文字列であり、登録語が0語なら空文字である

- **TC-003-1** 3語(スペースを含む語を含む)→ 登録順に `", "` で連結した文字列
- **TC-003-2** 0語 → 空文字
- **TC-003-3** words.json に3語を登録 → 認識時の context が、その登録順に `", "` で連結した文字列と一致する
- **TC-003-4** words.json が空配列 → 認識時の context が空文字

### SPEC-004 words.json が存在しない場合、認識は context を空文字で呼び、例外を出さない

- **TC-004-1** 存在しないパスを registry_path に指定して認識 → 例外なし・context が空文字

### SPEC-005 生成後に words.json が更新された場合、次の認識から更新後の登録語が context に反映される

- **TC-005-1** 1語で認識 → 語を追加して mtime を進める → 2回目の認識の context にだけ追加語が含まれる

### SPEC-024 context 付きの認識結果に含まれる、異なる登録語の数が3以上の場合、認識し直さずに空文字の結果を返す

- **TC-024-1** context 付きでは context 全文を返す Session → 戻り値の text が空文字、Session 呼び出しは1回
- **TC-024-2** 出力が全角・大小文字違いで登録語3語を含む → 戻り値の text が空文字、Session 呼び出しは1回

### SPEC-007 context 付きの認識結果に含まれる、異なる登録語の数が2以下の場合、認識し直さずにその結果を返す

- **TC-007-1** 出力に登録語2語 → Session 呼び出しは1回、戻り値はその出力
- **TC-007-2** 出力に同じ登録語が3回 → Session 呼び出しは1回、戻り値はその出力

### SPEC-008 words.json が JSON として読めない場合、例外を出さず直前の context を使い、読める状態に更新された後の認識から反映する

- **TC-008-1** 正常な words.json(1語)で認識 → 途中までの JSON に書き換えて mtime を進める → 認識が例外なく完了し、context は直前の1語のまま
- **TC-008-2** TC-008-1 の後、正常な JSON(2語)に書き換えて mtime を進める → 次の認識の context に2語目が含まれる
- **TC-008-3** 生成時点で words.json が壊れている → 生成と認識が例外なく完了し、context は空文字
