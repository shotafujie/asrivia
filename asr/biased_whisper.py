"""HuggingFace Whisper backend with contextual biasing support."""

from __future__ import annotations

import os
import re
import numpy as np
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration

from .biasing import WordRegistry, PrefixTree, HotwordLogitsProcessor


def extract_low_confidence_words(
    token_ids: list[int],
    log_probs: list[float],
    tokenizer,
    threshold: float = -2.0,
) -> list[str]:
    """Extract words with low confidence scores as OOV candidates.

    Returns words that look like proper nouns (katakana, short length)
    and have low log probability.
    """
    candidates = []

    # Decode individual tokens and find low-confidence spans
    decoded_tokens = [tokenizer.decode([tid]) for tid in token_ids]
    current_word = ""
    current_log_probs: list[float] = []

    for i, (token_text, lp) in enumerate(zip(decoded_tokens, log_probs)):
        # Token starts a new word if it starts with a space or is first
        if token_text.startswith(" ") or token_text.startswith("▁") or i == 0:
            if current_word and current_log_probs:
                avg_lp = sum(current_log_probs) / len(current_log_probs)
                if avg_lp < threshold and _looks_like_proper_noun(current_word):
                    candidates.append(current_word.strip())
            current_word = token_text
            current_log_probs = [lp]
        else:
            current_word += token_text
            current_log_probs.append(lp)

    # Handle last word
    if current_word and current_log_probs:
        avg_lp = sum(current_log_probs) / len(current_log_probs)
        if avg_lp < threshold and _looks_like_proper_noun(current_word):
            candidates.append(current_word.strip())

    return candidates


_KATAKANA_RE = re.compile(r"[\u30A0-\u30FF]+")


def _looks_like_proper_noun(word: str) -> bool:
    """Heuristic: katakana words 2-8 chars, or capitalized Latin words."""
    w = word.strip()
    if not w:
        return False
    # Katakana
    if _KATAKANA_RE.fullmatch(w) and 2 <= len(w) <= 8:
        return True
    # Capitalized Latin
    if w[0].isupper() and w.isascii() and 2 <= len(w) <= 20:
        return True
    return False


class BiasingWhisperBackend:
    """HuggingFace Whisper with hotword boosting."""

    def __init__(
        self,
        model_name: str = "openai/whisper-large-v3-turbo",
        language: str = "ja",
        registry_path: str = "words.json",
    ):
        self.model_name = model_name
        self.language = language
        self.registry_path = registry_path

        # Device setup (MPS for Apple Silicon)
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
            self.dtype = torch.float16
        else:
            self.device = torch.device("cpu")
            self.dtype = torch.float32

        print(f"[HF Whisper] モデルをロード中: {model_name} (device={self.device})")
        self.processor = WhisperProcessor.from_pretrained(model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(
            model_name, torch_dtype=self.dtype
        ).to(self.device)
        print("[HF Whisper] モデルのロードが完了しました")

        # Registry & tree
        self.registry = WordRegistry.load(registry_path)
        self.tree = PrefixTree()
        self._rebuild_tree()

        # Track file mtime for auto-reload
        self._registry_mtime: float = self._get_registry_mtime()

        # OOV candidate queue (filled during transcribe, consumed by UI)
        self.oov_candidates: list[str] = []

    def _get_registry_mtime(self) -> float:
        try:
            return os.path.getmtime(self.registry_path)
        except OSError:
            return 0.0

    def _rebuild_tree(self):
        words = self.registry.all()
        if words:
            self.tree.build(words, self.processor.tokenizer)
            print(f"[HF Whisper] PrefixTree構築完了: {len(words)}語登録")
        else:
            self.tree = PrefixTree()

    def reload_registry(self):
        """Reload word registry from disk and rebuild the prefix tree."""
        self.registry = WordRegistry.load(self.registry_path)
        self._rebuild_tree()
        self._registry_mtime = self._get_registry_mtime()

    def transcribe(self, audio: np.ndarray) -> dict:
        """Transcribe audio with hotword boosting.

        Returns a Whisper-compatible result dict: {"text": ..., "language": ...}
        """
        # Auto-reload registry if file changed
        current_mtime = self._get_registry_mtime()
        if current_mtime > self._registry_mtime:
            self.reload_registry()

        # Prepare input features
        input_features = self.processor(
            audio, sampling_rate=16000, return_tensors="pt"
        ).input_features.to(self.device, dtype=self.dtype)

        # Build logits processors
        logits_processors = []
        if len(self.registry) > 0:
            logits_processors.append(HotwordLogitsProcessor(self.tree))

        # Attention mask (pad_token == eos_token の警告対策)
        attention_mask = torch.ones(
            input_features.shape[:-1], dtype=torch.long, device=self.device
        )

        # Generate
        generate_kwargs = {
            "input_features": input_features,
            "attention_mask": attention_mask,
            "language": self.language if self.language != "auto" else None,
            "return_dict_in_generate": True,
            "output_logits": True,
        }
        if logits_processors:
            generate_kwargs["logits_processor"] = logits_processors

        with torch.no_grad():
            output = self.model.generate(**generate_kwargs)

        # Decode
        token_ids = output.sequences[0].tolist()
        text = self.processor.decode(token_ids, skip_special_tokens=True).strip()

        # Extract OOV candidates from logits
        self.oov_candidates = []
        if hasattr(output, "logits") and output.logits:
            log_probs = []
            # output.logits is a tuple of (batch, vocab_size) tensors per step
            generated_ids = token_ids[1:]  # skip decoder start token
            for step, logit_tensor in enumerate(output.logits):
                if step < len(generated_ids):
                    probs = torch.log_softmax(logit_tensor[0], dim=-1)
                    lp = probs[generated_ids[step]].item()
                    log_probs.append(lp)

            if log_probs:
                self.oov_candidates = extract_low_confidence_words(
                    generated_ids[: len(log_probs)],
                    log_probs,
                    self.processor.tokenizer,
                )

        return {
            "text": text,
            "language": self.language,
        }
