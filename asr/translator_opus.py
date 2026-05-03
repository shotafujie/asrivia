import sys
import time
import torch
from transformers import MarianMTModel, MarianTokenizer


class OpusTranslator:
    PAIRS = {
        ("ja", "en"): "Helsinki-NLP/opus-mt-ja-en",
        ("en", "ja"): "Helsinki-NLP/opus-mt-en-jap",
    }

    def __init__(self, device: str = "cpu", max_new_tokens: int = 128):
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.models = {}
        self.tokenizers = {}
        for pair, name in self.PAIRS.items():
            print(f"[OpusMT] ロード中: {name} ({pair[0]}->{pair[1]})")
            tok = MarianTokenizer.from_pretrained(name)
            mdl = MarianMTModel.from_pretrained(name).to(device)
            mdl.eval()
            self.tokenizers[pair] = tok
            self.models[pair] = mdl
        print("[OpusMT] ロード完了 / warmup中...")
        t0 = time.time()
        self.translate("こんにちは", "ja", "en")
        self.translate("hello", "en", "ja")
        print(f"[OpusMT] warmup完了 ({time.time()-t0:.2f}s)")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        pair = (source_lang, target_lang)
        if pair not in self.models:
            return f"[未対応の言語ペア: {source_lang}->{target_lang}]"
        try:
            tok = self.tokenizers[pair]
            mdl = self.models[pair]
            inputs = tok(text, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            with torch.no_grad():
                out = mdl.generate(**inputs, max_new_tokens=self.max_new_tokens, num_beams=1)
            return tok.decode(out[0], skip_special_tokens=True).strip()
        except Exception as e:
            print(f"[OpusMT例外]\n{e}", file=sys.stderr)
            return f"[翻訳エラー: {e}]"
