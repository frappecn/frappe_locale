#!/usr/bin/env python3
"""Keep only untranslated messages from a complete PO catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from babel.messages.catalog import Catalog, Message
from babel.messages.pofile import read_po, write_po


def is_untranslated(message: Message) -> bool:
	"""Return whether every translation value is empty."""
	if isinstance(message.string, dict):
		return not message.string or all(not value for value in message.string.values())

	return not message.string


def extract_untranslated(source: Path, output: Path) -> tuple[int, int]:
	with source.open("rb") as source_file:
		catalog = read_po(source_file)

	untranslated_catalog = Catalog(
		locale=catalog.locale,
		domain=catalog.domain,
		header_comment=catalog.header_comment,
		project=catalog.project,
		version=catalog.version,
		copyright_holder=catalog.copyright_holder,
		msgid_bugs_address=catalog.msgid_bugs_address,
		creation_date=catalog.creation_date,
		revision_date=catalog.revision_date,
		last_translator=catalog.last_translator,
		language_team=catalog.language_team,
		charset=catalog.charset,
		fuzzy=catalog.fuzzy,
	)
	untranslated_catalog.mime_headers = list(catalog.mime_headers)

	included = 0
	skipped = 0
	for message in catalog:
		if not message.id:
			continue

		if not is_untranslated(message):
			skipped += 1
			continue

		untranslated_catalog.add(
			message.id,
			string=message.string,
			locations=message.locations,
			flags=message.flags,
			auto_comments=message.auto_comments,
			user_comments=message.user_comments,
			previous_id=message.previous_id,
			context=message.context,
		)
		included += 1

	output.parent.mkdir(parents=True, exist_ok=True)
	with output.open("wb") as output_file:
		write_po(
			output_file,
			untranslated_catalog,
			sort_output=True,
			ignore_obsolete=True,
			width=None,
		)

	return included, skipped


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("source", type=Path, help="Complete source PO file")
	parser.add_argument("output", type=Path, help="Untranslated-only PO output file")
	args = parser.parse_args()

	included, skipped = extract_untranslated(args.source, args.output)
	print(f"Untranslated PO created at {args.output}")
	print(f"Included untranslated entries: {included}; skipped translated entries: {skipped}")


if __name__ == "__main__":
	main()
