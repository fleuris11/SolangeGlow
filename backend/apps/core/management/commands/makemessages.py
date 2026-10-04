from django.core.management.commands import makemessages


class Command(makemessages.Command):
    """makemessages without fuzzy matching: a guessed translation is worse than none."""

    msgmerge_options = [*makemessages.Command.msgmerge_options, "--no-fuzzy-matching"]
