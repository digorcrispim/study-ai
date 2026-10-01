import unicodedata


_TOPIC_ALIASES = {
    "custo benefício": "custo-benefício",
    "custo-benefício": "custo-benefício",
    "falácias": "falácias",
    "racionalidade": "racionalidade",
    "custos irrecuperáveis": "custos irrecuperáveis",
}


def canonical_topic_key(topic: str) -> str:
    normalized_topic = unicodedata.normalize("NFC", topic).strip()
    alias_key = normalized_topic.casefold()

    return _TOPIC_ALIASES.get(alias_key, normalized_topic)