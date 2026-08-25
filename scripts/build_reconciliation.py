from __future__ import annotations

import argparse
from pathlib import Path

from litigation_planner.reconciliation import (
    ReconciliationError,
    aggregate_fjc_ao_population,
    evaluate_ao_reconciliation,
    evaluate_review_packet,
    export_blinded_review_packet,
    export_candidate_mart,
    extract_recap_dockets,
    prepare_reconciliation_references,
    promote_reviewed_matches,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build private source-reconciliation inputs.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    recap = subcommands.add_parser("extract-recap")
    recap.add_argument("--source", type=Path, required=True)
    recap.add_argument("--manifest", type=Path, required=True)
    recap.add_argument("--output-root", type=Path, required=True)
    recap.add_argument("--contract", type=Path, default=Path("config/reconciliation.toml"))
    recap.add_argument("--batch-size", type=int, default=100_000)

    references = subcommands.add_parser("prepare-references")
    references.add_argument("--ao-table-c", type=Path, required=True)
    references.add_argument("--manifest", type=Path, required=True)
    references.add_argument("--output-root", type=Path, required=True)
    references.add_argument("--contract", type=Path, default=Path("config/reconciliation.toml"))

    fjc_ao = subcommands.add_parser("aggregate-fjc-ao")
    fjc_ao.add_argument("--source", type=Path, required=True)
    fjc_ao.add_argument("--manifest", type=Path, required=True)
    fjc_ao.add_argument("--output-root", type=Path, required=True)
    fjc_ao.add_argument("--contract", type=Path, default=Path("config/reconciliation.toml"))

    review = subcommands.add_parser("export-review")
    review.add_argument("--candidates", type=Path, required=True)
    review.add_argument("--output-root", type=Path, required=True)
    review.add_argument("--contract", type=Path, default=Path("config/reconciliation.toml"))

    evaluate = subcommands.add_parser("evaluate-review")
    evaluate.add_argument("--review", type=Path, required=True)
    evaluate.add_argument("--output-root", type=Path, required=True)
    evaluate.add_argument("--contract", type=Path, default=Path("config/reconciliation.toml"))

    promote = subcommands.add_parser("promote-matches")
    promote.add_argument("--warehouse", type=Path, required=True)
    promote.add_argument("--review-result", type=Path, required=True)
    promote.add_argument("--review-packet", type=Path, required=True)
    promote.add_argument("--candidates", type=Path, required=True)
    promote.add_argument("--output-root", type=Path, required=True)
    promote.add_argument("--contract", type=Path, default=Path("config/reconciliation.toml"))

    ao = subcommands.add_parser("evaluate-ao")
    ao.add_argument("--ao", type=Path, required=True)
    ao.add_argument("--fjc", type=Path, required=True)
    ao.add_argument("--output-root", type=Path, required=True)
    ao.add_argument("--contract", type=Path, default=Path("config/reconciliation.toml"))

    candidates = subcommands.add_parser("export-candidates")
    candidates.add_argument("--warehouse", type=Path, required=True)
    candidates.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "extract-recap":
        output = extract_recap_dockets(
            args.source, args.manifest, args.output_root, args.contract, args.batch_size
        )
    elif args.command == "prepare-references":
        output = prepare_reconciliation_references(
            args.ao_table_c, args.manifest, args.output_root, args.contract
        )
    elif args.command == "aggregate-fjc-ao":
        output = aggregate_fjc_ao_population(
            args.source, args.manifest, args.output_root, args.contract
        )
    elif args.command == "export-review":
        output = export_blinded_review_packet(args.candidates, args.output_root, args.contract)
    elif args.command == "evaluate-review":
        output = evaluate_review_packet(args.review, args.output_root, args.contract)
    elif args.command == "promote-matches":
        output = promote_reviewed_matches(
            args.warehouse,
            args.review_result,
            args.output_root,
            args.contract,
            review_packet_path=args.review_packet,
            candidates_path=args.candidates,
        )
    elif args.command == "evaluate-ao":
        output = evaluate_ao_reconciliation(args.ao, args.fjc, args.output_root, args.contract)
    else:
        output = export_candidate_mart(args.warehouse, args.output_root)
    print(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconciliationError as error:
        raise SystemExit(f"reconciliation failed: {error}") from error
