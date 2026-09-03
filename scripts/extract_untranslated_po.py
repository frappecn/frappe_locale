#!/usr/bin/env python3
"""Keep only untranslated messages from one or more complete PO catalogs."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from babel.messages.catalog import Catalog, Message
from babel.messages.pofile import read_po, write_po


def is_untranslated(message: Message) -> bool:
	"""Return whether every translation value is empty."""
	if isinstance(message.string, dict):
		return not message.string or all(not value for value in message.string.values())

	return not message.string


def has_translation(message: Message) -> bool:
	"""Return whether a message contains any manual translation value."""
	if isinstance(message.string, dict):
		return any(bool(value) for value in message.string.values())

	return bool(message.string)


def add_message(target: Catalog, source: Message, translation: Message | None = None) -> None:
	"""Add a source message, optionally using a translation from the existing output."""
	message = translation or source
	flags = list(dict.fromkeys((*source.flags, *message.flags)))
	auto_comments = list(dict.fromkeys((*source.auto_comments, *message.auto_comments)))
	user_comments = list(dict.fromkeys((*source.user_comments, *message.user_comments)))

	target.add(
		source.id,
		string=message.string,
		locations=source.locations,
		flags=flags,
		auto_comments=auto_comments,
		user_comments=user_comments,
		previous_id=source.previous_id,
		context=source.context,
	)


def extract_untranslated(sources: Sequence[Path], output: Path) -> tuple[int, int, int]:
	catalogs: list[Catalog] = []
	for source in sources:
		with source.open("rb") as source_file:
			catalogs.append(read_po(source_file))

	if not catalogs:
		raise ValueError("At least one source PO file is required")

	existing_messages: dict[tuple[str | None, object], Message] = {}
	if output.exists():
		with output.open("rb") as output_file:
			existing_catalog = read_po(output_file)
		existing_messages = {
			(message.context, message.id): message
			for message in existing_catalog
			if message.id
		}

	source_messages: dict[tuple[str | None, object], Message] = {}
	untranslated_keys: set[tuple[str | None, object]] = set()
	for catalog in catalogs:
		for message in catalog:
			if not message.id:
				continue

			key = (message.context, message.id)
			if key not in source_messages or (
				is_untranslated(message) and not is_untranslated(source_messages[key])
			):
				source_messages[key] = message
			if is_untranslated(message):
				untranslated_keys.add(key)

	first_catalog = catalogs[0]
	untranslated_catalog = Catalog(
		locale=first_catalog.locale,
		domain=first_catalog.domain,
		header_comment=first_catalog.header_comment,
		project=first_catalog.project,
		version=first_catalog.version,
		copyright_holder=first_catalog.copyright_holder,
		msgid_bugs_address=first_catalog.msgid_bugs_address,
		creation_date=first_catalog.creation_date,
		revision_date=first_catalog.revision_date,
		last_translator=first_catalog.last_translator,
		language_team=first_catalog.language_team,
		charset=first_catalog.charset,
		fuzzy=first_catalog.fuzzy,
	)
	untranslated_catalog.mime_headers = list(first_catalog.mime_headers)

	included = 0
	preserved = 0
	skipped = 0
	for key, message in source_messages.items():
		existing = existing_messages.get(key)
		if existing and has_translation(existing):
			add_message(untranslated_catalog, message, existing)
			preserved += 1
			continue

		if key not in untranslated_keys:
			skipped += 1
			continue

		add_message(untranslated_catalog, message)
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
	output.write_bytes(output.read_bytes().rstrip(b"\n") + b"\n")

	return included, preserved, skipped


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"sources",
		type=Path,
		nargs="+",
		help="One or more complete source PO files",
	)
	parser.add_argument("output", type=Path, help="Untranslated-only PO output file")
	args = parser.parse_args()

	included, preserved, skipped = extract_untranslated(args.sources, args.output)
	print(f"Untranslated PO created at {args.output}")
	print(
		f"Included untranslated entries: {included}; "
		f"preserved manual translations: {preserved}; "
		f"skipped translated entries: {skipped}"
	)


if __name__ == "__main__":
	main()
