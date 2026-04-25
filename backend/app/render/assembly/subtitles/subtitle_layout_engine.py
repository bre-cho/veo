from __future__ import annotations

from typing import List


def group_words_readable(
    words: List[dict],
    max_words_per_line: int,
    max_chars_per_line: int,
) -> List[List[dict]]:
    """Split a word list into subtitle line groups respecting both word and character limits.

    Groups are broken whenever adding the next word would exceed *max_words_per_line*
    **or** would push the running character count beyond *max_chars_per_line*.

    Args:
        words: List of word-timing dicts (must have a ``word`` key).
        max_words_per_line: Hard cap on the number of words per line.
        max_chars_per_line: Hard cap on the number of characters per line
            (words joined by single spaces).

    Returns:
        A list of groups, where each group is a non-empty list of word dicts.
    """
    groups: List[List[dict]] = []
    current: List[dict] = []
    current_chars = 0

    for word_dict in words:
        text = word_dict["word"]
        # +1 accounts for the space separator between words.  It is omitted
        # for the first word in a new group (no leading space needed).
        projected_chars = current_chars + len(text) + (1 if current else 0)

        if current and (
            len(current) >= max_words_per_line
            or projected_chars > max_chars_per_line
        ):
            groups.append(current)
            current = [word_dict]
            current_chars = len(text)
        else:
            current.append(word_dict)
            current_chars = projected_chars

    if current:
        groups.append(current)

    return groups
