#!/usr/bin/env python3
"""Create a sparse PO catalog from a complete translation catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from babel.messages.catalog import Catalog, Message
from babel.messages.pofile import read_po, write_po


def has_complete_translation(message: Message) -> bool:
	"""Return whether a message has a usable translation."""
	if isinstance(message.string, dict):
		return bool(message.string) and all(bool(value) for value in message.string.values())

	return bool(message.string)


def build_sparse_po(source: Path, output: Path, locale: str) -> tuple[int, int]:
	with source.open("rb") as source_file:
		catalog = read_po(source_file)

	overlay = Catalog(
		locale=locale,
		domain="messages",
		project="frappe_locale",
		version="1.0",
		charset="UTF-8",
		fuzzy=False,
	)

	included = 0
	skipped = 0
	for message in catalog:
		# Skip the PO header, fuzzy entries, and untranslated messages.
		if not message.id or message.fuzzy or not has_complete_translation(message):
			skipped += 1
			continue

		overlay.add(
			message.id,
			string=message.string,
			context=message.context,
		)
		included += 1

	output.parent.mkdir(parents=True, exist_ok=True)
	with output.open("wb") as output_file:
		write_po(
			output_file,
			overlay,
			sort_output=True,
			ignore_obsolete=True,
			width=None,
		)

	return included, skipped


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("source", type=Path, help="Complete source PO file")
	parser.add_argument("output", type=Path, help="Sparse PO output file")
	parser.add_argument("--locale", default="zh", help="Locale code used in the output catalog")
	args = parser.parse_args()

	included, skipped = build_sparse_po(args.source, args.output, args.locale)
	print(f"Sparse PO created at {args.output}")
	print(f"Included translated entries: {included}; skipped entries: {skipped}")


if __name__ == "__main__":
	main()
