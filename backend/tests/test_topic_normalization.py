import unittest

from backend.services.topic_normalization import canonical_topic_key


class CanonicalTopicKeyTests(unittest.TestCase):
    def test_approved_alias_variants_share_canonical_keys(self):
        aliases = {
            "custo-benefício": [
                "Custo benefício",
                "custo-benefício",
                "Custo-benefício",
            ],
            "falácias": ["falácias", "Falácias"],
            "racionalidade": ["racionalidade", "Racionalidade"],
            "custos irrecuperáveis": [
                "custos irrecuperáveis",
                "Custos irrecuperáveis",
            ],
        }

        for expected_key, variants in aliases.items():
            with self.subTest(expected_key=expected_key):
                for variant in variants:
                    with self.subTest(variant=variant):
                        self.assertEqual(
                            canonical_topic_key(variant),
                            expected_key,
                        )

    def test_unapproved_pairs_remain_distinct(self):
        distinct_pairs = [
            ("Custo de oportunidade", "Custos de oportunidade"),
            ("Racionalidade", "Racionalidade e custo benefício"),
            ("Racionalidade", "Tipos de racionalidade"),
            ("Falácias", "Falácia: custos irrecuperáveis"),
            ("Falácias", "Falácia: média vs marginal"),
            (
                "Falácias",
                "Falácia: medir proporções vs valores absolutos",
            ),
            ("Falácias", "Falácias (custos irrecuperáveis)"),
            ("Custo-benefício", "Análise custo-benefício"),
        ]

        for first, second in distinct_pairs:
            with self.subTest(first=first, second=second):
                self.assertNotEqual(
                    canonical_topic_key(first),
                    canonical_topic_key(second),
                )

    def test_strips_only_outer_whitespace(self):
        self.assertEqual(
            canonical_topic_key("  Custo benefício \t"),
            "custo-benefício",
        )
        self.assertEqual(
            canonical_topic_key("  Tema  desconhecido  "),
            "Tema  desconhecido",
        )

    def test_unicode_nfc_equivalent_values_match(self):
        decomposed = "Racionalidade e cafe\u0301"
        composed = "Racionalidade e café"

        self.assertEqual(
            canonical_topic_key(decomposed),
            canonical_topic_key(composed),
        )

    def test_unknown_topics_preserve_case_hyphens_and_words(self):
        self.assertEqual(
            canonical_topic_key("Análise custo-benefício"),
            "Análise custo-benefício",
        )
        self.assertEqual(
            canonical_topic_key("Análise custo benefício"),
            "Análise custo benefício",
        )
        self.assertNotEqual(
            canonical_topic_key("Análise custo-benefício"),
            canonical_topic_key("Análise custo benefício"),
        )
        self.assertEqual(canonical_topic_key("Tema Novo"), "Tema Novo")
        self.assertNotEqual(
            canonical_topic_key("Tema Novo"),
            canonical_topic_key("tema novo"),
        )

    def test_canonical_keys_are_idempotent(self):
        canonical_keys = [
            "custo-benefício",
            "falácias",
            "racionalidade",
            "custos irrecuperáveis",
        ]

        for canonical_key in canonical_keys:
            with self.subTest(canonical_key=canonical_key):
                self.assertEqual(
                    canonical_topic_key(canonical_topic_key(canonical_key)),
                    canonical_key,
                )

    def test_function_is_deterministic(self):
        topic = "  Custo benefício  "

        self.assertEqual(
            canonical_topic_key(topic),
            canonical_topic_key(topic),
        )

    def test_original_input_remains_unchanged(self):
        topic = "  Custo benefício  "

        canonical_topic_key(topic)

        self.assertEqual(topic, "  Custo benefício  ")


if __name__ == "__main__":
    unittest.main()