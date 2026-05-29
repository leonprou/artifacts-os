"""cli set command — write a single frontmatter property to an artifact."""

from artifacts_os.core import Registry, set_prop


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "set",
        help="write a single frontmatter property (transition-validated)",
    )
    p.add_argument("ref", help="artifact reference (name, id, or partial)")
    p.add_argument("property", help="property name")
    p.add_argument("value", help="new value")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    artifact = set_prop(registry, args.ref, args.property, args.value)
    print(f"{artifact.path.stem}: {args.property}={artifact.frontmatter.get(args.property)!r}")
    return 0
