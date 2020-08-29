from argparse import _AppendAction
from difflib import unified_diff
import io
import logging
import os


logger = logging.getLogger(__name__)


class DiscardDefaultIfSpecifiedAppendAction(_AppendAction):

    """
    Fixes bug http://bugs.python.org/issue16399 for 'append' action
    """

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(self, "_discarded_default", None) is None:
            setattr(namespace, self.dest, [])
            self._discarded_default = True  # pylint: disable=attribute-defined-outside-init

        super().__call__(
            parser, namespace, values, option_string=None
        )


def keyvaluestring(d):
    return ", ".join("{}={}".format(k, v) for k, v in sorted(d.items()))


def prefixed_environ():
    return {"${}".format(key): value for key, value in os.environ.items()}


class ConfiguredFile:
    def __init__(self, path, versionconfig):
        self.path = path
        self._versionconfig = versionconfig

    def should_contain_version(self, version, context):

        context["current_version"] = self._versionconfig.serialize(version, context)

        serialized_version = self._versionconfig.search.format(**context)

        if self.contains(serialized_version):
            return

        msg = "Did not find '{}' or '{}' in file {}".format(
            version.original, serialized_version, self.path
        )

        if version.original:
            assert self.contains(version.original), msg
            return

        assert False, msg

    def contains(self, search):
        with open(self.path, "rt", encoding="utf-8") as f:
            search_lines = search.splitlines()
            lookbehind = []

            for lineno, line in enumerate(f.readlines()):
                lookbehind.append(line.rstrip("\n"))

                if len(lookbehind) > len(search_lines):
                    lookbehind = lookbehind[1:]

                if (
                    search_lines[0] in lookbehind[0]
                    and search_lines[-1] in lookbehind[-1]
                    and search_lines[1:-1] == lookbehind[1:-1]
                ):
                    logger.info(
                        "Found '%s' in %s at line %s: %s",
                        search,
                        self.path,
                        lineno - (len(lookbehind) - 1),
                        line.rstrip(),
                    )
                    return True
        return False

    def replace(self, current_version, new_version, context, dry_run):

        with open(self.path, "rt", encoding="utf-8") as f:
            file_content_before = f.read()
            file_new_lines = f.newlines

        context["current_version"] = self._versionconfig.serialize(
            current_version, context
        )
        context["new_version"] = self._versionconfig.serialize(new_version, context)

        search_for = self._versionconfig.search.format(**context)
        replace_with = self._versionconfig.replace.format(**context)

        file_content_after = file_content_before.replace(search_for, replace_with)

        if file_content_before == file_content_after:
            # TODO expose this to be configurable
            file_content_after = file_content_before.replace(
                current_version.original, replace_with
            )

        if file_content_before != file_content_after:
            logger.info("%s file %s:", "Would change" if dry_run else "Changing", self.path)
            logger.info(
                "\n".join(
                    list(
                        unified_diff(
                            file_content_before.splitlines(),
                            file_content_after.splitlines(),
                            lineterm="",
                            fromfile="a/" + self.path,
                            tofile="b/" + self.path,
                        )
                    )
                )
            )
        else:
            logger.info("%s file %s", "Would not change" if dry_run else "Not changing", self.path)

        if not dry_run:
            with open(self.path, "wt", encoding="utf-8", newline=file_new_lines) as f:
                f.write(file_content_after)

    def __str__(self):
        return self.path

    def __repr__(self):
        return "<bumpversion.ConfiguredFile:{}>".format(self.path)
