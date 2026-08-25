from unittest import TestCase

from scripts.check_public_boundary import ROOT, violations


class PublicBoundaryTest(TestCase):
    def test_rejects_private_and_dataset_paths(self) -> None:
        paths = [ROOT / ".project/state.md", ROOT / "data/cases.csv"]
        self.assertEqual(len(violations(paths)), 2)

    def test_accepts_source_and_contracts(self) -> None:
        paths = [ROOT / "src/litigation_planner/api.py", ROOT / "docs/data-contract.md"]
        self.assertEqual(violations(paths), [])
