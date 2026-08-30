import html
import re
from typing import List

from common.enumerator import Language

# Patterns commonly used in prompt injection attacks
_INJECTION_PATTERNS = [
    re.compile(r'\[SYSTEM\]', re.IGNORECASE),
    re.compile(r'\[INST\]', re.IGNORECASE),
    re.compile(r'<<SYS>>', re.IGNORECASE),
    re.compile(r'忽略.*指令', re.IGNORECASE),
    re.compile(r'disregard.*instructions', re.IGNORECASE),
    re.compile(r'你现在是', re.IGNORECASE),
    re.compile(r'you are now', re.IGNORECASE),
    re.compile(r'重复.*prompt', re.IGNORECASE),
    re.compile(r'repeat.*prompt', re.IGNORECASE),
    re.compile(r'ignore.*previous', re.IGNORECASE),
    re.compile(r'forget.*rules', re.IGNORECASE),
]


def sanitize_user_input(text: str, max_length: int = 2000) -> str:
    """Sanitize user input to mitigate prompt injection attacks."""
    if not text:
        return text
    text = text[:max_length]
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub('[已过滤]', text)
    return html.escape(text)


def is_blank(s: str) -> bool:
    """Check if a string is None, empty, or contains only whitespace."""
    return s is None or not s.strip() or s == ""


def split_by_punc(text: str, lang: Language) -> List[str]:
    if lang == Language.ZH:
        cut_punc = "，。！？"
    elif lang == Language.JA:
        cut_punc = "、。！？"
    else:
        cut_punc = ",.!?"

    def punc_cut(text: str, punc: str):
        texts = []
        last = -1
        for i in range(len(text)):
            if text[i] in punc:
                try:
                    texts.append(text[last + 1: i])
                except IndexError:
                    continue
                last = i
        return texts

    return punc_cut(text, cut_punc)
