"""Prefix tree for token-level hotword matching."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _TrieNode:
    children: dict[int, _TrieNode] = field(default_factory=dict)
    boost: float = 0.0  # non-zero at leaf nodes
    depth: int = 0       # depth in this word's token sequence
    total_tokens: int = 0  # total token count of the word (for per-token split)
    is_end: bool = False


class PrefixTree:
    """Token-level prefix tree for hotword boosting.

    Each registered word is tokenized and inserted into a trie.
    During decoding, `get_next_boost` looks at recent token history
    and returns candidate next-token boosts.
    """

    def __init__(self):
        self._root = _TrieNode()

    def build(self, words: list, tokenizer) -> None:
        """Build the prefix tree from a list of BiasWord objects.

        For each word, tokenize with and without a leading space to handle
        Whisper's context-dependent spacing.
        """
        self._root = _TrieNode()

        for bw in words:
            variants = [bw.word]
            # Add space-prefixed variant for subword tokenizers
            if not bw.word.startswith(" "):
                variants.append(" " + bw.word)

            for variant in variants:
                token_ids = tokenizer.encode(variant)
                if not token_ids:
                    continue
                # Per-token boost: distribute evenly across tokens
                per_token = bw.boost / len(token_ids)
                self._insert(token_ids, per_token)

    def _insert(self, token_ids: list[int], per_token_boost: float) -> None:
        node = self._root
        total = len(token_ids)
        for depth, tid in enumerate(token_ids):
            if tid not in node.children:
                node.children[tid] = _TrieNode()
            node = node.children[tid]
            node.depth = depth + 1
            node.total_tokens = total
        node.is_end = True
        node.boost = per_token_boost

    def get_next_boost(self, token_history: list[int]) -> dict[int, float]:
        """Given recent token history, return {next_token_id: boost} for
        all hotword prefixes that match the tail of token_history."""
        result: dict[int, float] = {}

        # Try matching from each position in the history
        for start in range(len(token_history)):
            node = self._root
            matched = True
            for tid in token_history[start:]:
                if tid in node.children:
                    node = node.children[tid]
                else:
                    matched = False
                    break

            if matched:
                # Add all possible next tokens from this node
                for next_tid, child in node.children.items():
                    # Use per-token boost (stored at leaf, but uniform across path)
                    boost = child.boost if child.is_end else self._get_leaf_boost(child)
                    if boost > 0:
                        # Take max if multiple paths suggest the same token
                        result[next_tid] = max(result.get(next_tid, 0.0), boost)

        # Also check if any hotword starts at the next position (fresh match)
        for next_tid, child in self._root.children.items():
            boost = child.boost if child.is_end else self._get_leaf_boost(child)
            if boost > 0:
                result[next_tid] = max(result.get(next_tid, 0.0), boost)

        return result

    def _get_leaf_boost(self, node: _TrieNode) -> float:
        """Walk down to find the boost value from any leaf under this node."""
        if node.is_end:
            return node.boost
        for child in node.children.values():
            b = self._get_leaf_boost(child)
            if b > 0:
                return b
        return 0.0
