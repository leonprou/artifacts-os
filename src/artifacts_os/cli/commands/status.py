"""cli status command — update an artifact's status."""

from artifacts_os.core import update, Registry


def register(subparsers) -> None:
    p = subparsers.add_parser("status", help="update artifact status")
    p.add_argument("ref", help="artifact reference")
    p.add_argument("new_status", metavar="new-status", help="new status value")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    artifact = update(registry, args.ref, status=args.new_status)
    print(f"{artifact.path.stem}: {artifact.status}")
    return 0
