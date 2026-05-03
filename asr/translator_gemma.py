import sys
import time
from mlx_lm import load, generate


class GemmaTranslator:
    def __init__(self, model_id: str = "mlx-community/translategemma-4b-it-8bit", max_tokens: int = 128):
        print(f"[TranslateGemma] モデルをロード中: {model_id}")
        self.model, self.tokenizer = load(model_id)
        self.max_tokens = max_tokens
        print("[TranslateGemma] ロード完了 / warmup中...")
        t0 = time.time()
        self.translate("こんにちは", "ja", "en")
        print(f"[TranslateGemma] warmup完了 ({time.time()-t0:.2f}s)")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            messages = [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "source_lang_code": source_lang,
                    "target_lang_code": target_lang,
                    "text": text,
                }],
            }]
            prompt = self.tokenizer.apply_chat_template(
                messages, add_generation_prompt=True
            )
            output = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=self.max_tokens,
                verbose=False,
            )
            for tok in ("<end_of_turn>", "<start_of_turn>", "<eos>", "<bos>"):
                output = output.replace(tok, "")
            return output.strip()
        except Exception as e:
            print(f"[TranslateGemma例外]\n{e}", file=sys.stderr)
            return f"[翻訳エラー: {e}]"
