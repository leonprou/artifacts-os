"""cli create command — create a new artifact."""

from artifacts_os.core import create, Registry


def register(subparsers) -> None:
    p = subparsers.add_parser("create", help="create a new artifact")
    p.add_argument("title", help="artifact title")
    p.add_argument("--kind", "-k", default="task", help="artifact kind (default: task)")
    p.add_argument("--body", "-b", default="", help="artifact body text")
    p.add_argument(
        "--fields",
        "-f",
        nargs="*",
        metavar="KEY=VALUE",
        help="extra frontmatter fields (e.g. status=ready priority=high)",
    )
    p.set_defaults(func=run)


def _parse_fields(field_args: list[str] | None) -> dict:
    if not field_args:
        return {}
    fields = {}
    for item in field_args:
        if "=" not in item:
            raise ValueError(f"Invalid field spec {item!r} — expected KEY=VALUE")
        key, _, value = item.partition("=")
        fields[key.strip()] = value.strip()
    return fields


def run(args, registry: Registry) -> int:
    fields = _parse_fields(args.fields)
    artifact = create(
        registry,
        args.kind,
        args.title,
        body=args.body,
        fields=fields,
    )
    print(artifact.name)
    return 0
