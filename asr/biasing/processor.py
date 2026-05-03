"""HuggingFace LogitsProcessor for hotword boosting."""

from __future__ import annotations

import torch
from transformers import LogitsProcessor

from .tree import PrefixTree


class HotwordLogitsProcessor(LogitsProcessor):
    """Applies contextual biasing scores during beam search / greedy decoding.

    For each beam, looks at the recent token history and boosts logits
    for tokens that continue a registered hotword prefix.
    """

    def __init__(self, tree: PrefixTree, window_size: int = 10):
        self.tree = tree
        self.window_size = window_size

    def __call__(
        self,
        input_ids: torch.LongTensor,   # (batch * beams, seq_len)
        scores: torch.FloatTensor,      # (batch * beams, vocab_size)
    ) -> torch.FloatTensor:
        for beam_idx in range(scores.shape[0]):
            ids = input_ids[beam_idx].tolist()
            window = ids[-self.window_size:]

            next_boosts = self.tree.get_next_boost(window)
            for token_id, boost in next_boosts.items():
                if 0 <= token_id < scores.shape[1]:
                    scores[beam_idx, token_id] += boost

        return scores
