import argparse
from datetime import datetime
import io
import itertools
import logging
import os
import re
import sre_constants
import sys
import warnings
from configparser import (
    ConfigParser,
    RawConfigParser,
    NoOptionError,
)

from bumpversion import __version__, __title__
from bumpversion.version_part import (
    VersionConfig,
    NumericVersionPartConfiguration,
    ConfiguredVersionPartConfiguration,
)
from bumpversion.exceptions import (
    IncompleteVersionRepresentationException,
    MissingValueForSerializationException,
    WorkingDirectoryIsDirtyException,
)

from bumpversion.utils import (
    ConfiguredFile,
    DiscardDefaultIfSpecifiedAppendAction,
    keyvaluestring,
    prefixed_environ,
)
from bumpversion.vcs import Git, Mercurial


DESCRIPTION = "{}: v{} (using Python v{})".format(
    __title__,
    __version__,
    sys.version.split("\n")[0].split(" ")[0]
)
VCS = [Git, Mercurial]


logger_list = logging.getLogger("bumpversion.list")
logger = logging.getLogger(__name__)
time_context = {"now": datetime.now(), "utcnow": datetime.utcnow()}


OPTIONAL_ARGUMENTS_THAT_TAKE_VALUES = [
    "--config-file",
    "--current-version",
    "--message",
    "--new-version",
    "--parse",
    "--serialize",
    "--search",
    "--replace",
    "--tag-name",
    "--tag-message",
    "-m",
]


def main(original_args=None):
    # determine configuration based on command-line arguments
    # and on-disk configuration files
    args, known_args, root_parser, positionals = _parse_arguments_phase_1(original_args)
    _setup_logging(known_args.list, known_args.verbose)
    vcs_info = _determine_vcs_usability()
    defaults = _determine_current_version(vcs_info)
    explicit_config = None
    if hasattr(known_args, "config_file"):
        explicit_config = known_args.config_file
    config_file = _determine_config_file(explicit_config)
    config, config_file_exists, config_newlines, part_configs, files = _load_configuration(
        config_file, explicit_config, defaults,
    )
    known_args, parser2, remaining_argv = _parse_arguments_phase_2(
        args, known_args, defaults, root_parser
    )
    version_config = _setup_versionconfig(known_args, part_configs)
    current_version = version_config.parse(known_args.current_version)
    context = dict(
        itertools.chain(time_context.items(), prefixed_environ().items(), vcs_info.items())
    )

    # calculate the desired new version
    new_version = _assemble_new_version(
        context, current_version, defaults, known_args.current_version, positionals, version_config
    )
    args, file_names = _parse_arguments_phase_3(remaining_argv, positionals, defaults, parser2)
    new_version = _parse_new_version(args, new_version, version_config)

    # replace version in target files
    vcs = _determine_vcs_dirty(VCS, defaults)
    files.extend(
        ConfiguredFile(file_name, version_config)
        for file_name
        in (file_names or positionals[1:])
    )
    _check_files_contain_version(files, current_version, context)
    _replace_version_in_files(files, current_version, new_version, args.dry_run, context)
    _log_list(config, args.new_version)

    # store the new version
    _update_config_file(
        config, config_file, config_newlines, config_file_exists, args.new_version, args.dry_run,
    )

    # commit and tag
    if vcs:
        context = _commit_to_vcs(files, context, config_file, config_file_exists, vcs,
                                 args, current_version, new_version)
        _tag_in_vcs(vcs, context, args)


def split_args_in_optional_and_positional(args):
    # manually parsing positional arguments because stupid argparse can't mix
    # positional and optional arguments

    positions = []
    for i, arg in enumerate(args):

        previous = None

        if i > 0:
            previous = args[i - 1]

        if (not arg.startswith("-")) and (
            previous not in OPTIONAL_ARGUMENTS_THAT_TAKE_VALUES
        ):
            positions.append(i)

    positionals = [arg for i, arg in enumerate(args) if i in positions]
    args = [arg for i, arg in enumerate(args) if i not in positions]

    return (positionals, args)


def _parse_arguments_phase_1(original_args):
    positionals, args = split_args_in_optional_and_positional(
        sys.argv[1:] if original_args is None else original_args
    )
    if len(positionals[1:]) > 2:
        warnings.warn(
            "Giving multiple files on the command line will be deprecated, "
            "please use [bumpversion:file:...] in a config file.",
            PendingDeprecationWarning,
        )
    root_parser = argparse.ArgumentParser(add_help=False)
    root_parser.add_argument(
        "--config-file",
        metavar="FILE",
        default=argparse.SUPPRESS,
        required=False,
        help="Config file to read most of the variables from (default: .bumpversion.cfg)",
    )
    root_parser.add_argument(
        "--verbose",
        action="count",
        default=0,
        help="Print verbose logging to stderr",
        required=False,
    )
    root_parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List machine readable information",
        required=False,
    )
    root_parser.add_argument(
        "--allow-dirty",
        action="store_true",
        default=False,
        help="Don't abort if working directory is dirty",
        required=False,
    )
    known_args, _ = root_parser.parse_known_args(args)
    return args, known_args, root_parser, positionals


def _setup_logging(show_list, verbose):
    logformatter = logging.Formatter("%(message)s")
    if not logger_list.handlers:
        ch2 = logging.StreamHandler(sys.stdout)
        ch2.setFormatter(logformatter)
        logger_list.addHandler(ch2)
    if show_list:
        logger_list.setLevel(logging.DEBUG)
    try:
        log_level = [logging.WARNING, logging.INFO, logging.DEBUG][verbose]
    except IndexError:
        log_level = logging.DEBUG
    root_logger = logging.getLogger('')
    root_logger.setLevel(log_level)
    logger.debug("Starting %s", DESCRIPTION)


def _determine_vcs_usability():
    vcs_info = {}
    for vcs in VCS:
        if vcs.is_usable():
            vcs_info.update(vcs.latest_tag_info())
    return vcs_info


def _determine_current_version(vcs_info):
    defaults = {}
    if "current_version" in vcs_info:
        defaults["current_version"] = vcs_info["current_version"]
    return defaults


def _determine_config_file(explicit_config):
    if explicit_config:
        return explicit_config
    if not os.path.exists(".bumpversion.cfg") and os.path.exists("setup.cfg"):
        return "setup.cfg"
    return ".bumpversion.cfg"


def _load_configuration(config_file, explicit_config, defaults):
    # setup.cfg supports interpolation - for compatibility we must do the same.
    if os.path.basename(config_file) == "setup.cfg":
        config = ConfigParser("")
    else:
        config = RawConfigParser("")
    # don't transform keys to lowercase (which would be the default)
    config.optionxform = lambda option: option
    config.add_section("bumpversion")
    config_file_exists = os.path.exists(config_file)

    if not config_file_exists:
        message = "Could not read config file at {}".format(config_file)
        if explicit_config:
            raise argparse.ArgumentTypeError(message)
        logger.info(message)
        return config, config_file_exists, None, {}, []

    logger.info("Reading config file %s:", config_file)

    with open(config_file, "rt", encoding="utf-8") as config_fp:
        config_content = config_fp.read()
        config_newlines = config_fp.newlines

    # TODO: this is a DEBUG level log
    logger.info(config_content)
    config.read_string(config_content)
    log_config = io.StringIO()
    config.write(log_config)

    if config.has_option("bumpversion", "files"):
        warnings.warn(
            "'files =' configuration will be deprecated, please use [bumpversion:file:...]",
            PendingDeprecationWarning,
        )

    defaults.update(dict(config.items("bumpversion")))

    for listvaluename in ("serialize",):
        try:
            value = config.get("bumpversion", listvaluename)
            defaults[listvaluename] = list(
                filter(None, (x.strip() for x in value.splitlines()))
            )
        except NoOptionError:
            pass  # no default value then ;)

    for boolvaluename in ("commit", "tag", "dry_run"):
        try:
            defaults[boolvaluename] = config.getboolean(
                "bumpversion", boolvaluename
            )
        except NoOptionError:
            pass  # no default value then ;)

    part_configs = {}
    files = []
    file_or_part = re.compile("^bumpversion:(file|part):(.+)")
    for section_name in config.sections():
        section_name_match = file_or_part.match(section_name)

        if not section_name_match:
            continue

        section_prefix, section_value = section_name_match.groups()

        section_config = dict(config.items(section_name))

        if section_prefix == "part":
            ThisVersionPartConfiguration = NumericVersionPartConfiguration

            if "values" in section_config:
                section_config["values"] = list(
                    filter(
                        None,
                        (x.strip() for x in section_config["values"].splitlines()),
                    )
                )
                ThisVersionPartConfiguration = ConfiguredVersionPartConfiguration

            part_configs[section_value] = ThisVersionPartConfiguration(
                **section_config
            )

        elif section_prefix == "file":
            filename = section_value

            if "serialize" in section_config:
                section_config["serialize"] = list(
                    filter(
                        None,
                        (
                            x.strip().replace("\\n", "\n")
                            for x in section_config["serialize"].splitlines()
                        ),
                    )
                )

            section_config["part_configs"] = part_configs

            if "parse" not in section_config:
                section_config["parse"] = defaults.get(
                    "parse", r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
                )

            if "serialize" not in section_config:
                section_config["serialize"] = defaults.get(
                    "serialize", ["{major}.{minor}.{patch}"]
                )

            if "search" not in section_config:
                section_config["search"] = defaults.get(
                    "search", "{current_version}"
                )

            if "replace" not in section_config:
                section_config["replace"] = defaults.get("replace", "{new_version}")

            files.append(ConfiguredFile(filename, VersionConfig(**section_config)))

    return config, config_file_exists, config_newlines, part_configs, files


def _parse_arguments_phase_2(args, known_args, defaults, root_parser):
    parser2 = argparse.ArgumentParser(
        prog="bumpversion", add_help=False, parents=[root_parser]
    )
    parser2.set_defaults(**defaults)
    parser2.add_argument(
        "--current-version",
        metavar="VERSION",
        help="Version that needs to be updated",
        required=False,
    )
    parser2.add_argument(
        "--parse",
        metavar="REGEX",
        help="Regex parsing the version string",
        default=defaults.get(
            "parse", r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        ),
    )
    parser2.add_argument(
        "--serialize",
        metavar="FORMAT",
        action=DiscardDefaultIfSpecifiedAppendAction,
        help="How to format what is parsed back to a version",
        default=defaults.get("serialize", ["{major}.{minor}.{patch}"]),
    )
    parser2.add_argument(
        "--search",
        metavar="SEARCH",
        help="Template for complete string to search",
        default=defaults.get("search", "{current_version}"),
    )
    parser2.add_argument(
        "--replace",
        metavar="REPLACE",
        help="Template for complete string to replace",
        default=defaults.get("replace", "{new_version}"),
    )
    known_args, remaining_argv = parser2.parse_known_args(args)

    defaults.update(vars(known_args))

    assert isinstance(known_args.serialize, list), "Argument `serialize` must be a list"

    return known_args, parser2, remaining_argv


def _setup_versionconfig(known_args, part_configs):
    try:
        version_config = VersionConfig(
            parse=known_args.parse,
            serialize=known_args.serialize,
            search=known_args.search,
            replace=known_args.replace,
            part_configs=part_configs,
        )
    except sre_constants.error:
        # TODO: use re.error here mayhaps, also: should we log?
        sys.exit(1)
    return version_config


def _assemble_new_version(
    context, current_version, defaults, arg_current_version, positionals, version_config
):
    new_version = None
    if "new_version" not in defaults and arg_current_version:
        try:
            if current_version and positionals:
                logger.info("Attempting to increment part '%s'", positionals[0])
                new_version = current_version.bump(positionals[0], version_config.order())
                logger.info("Values are now: %s", keyvaluestring(new_version._values))
                defaults["new_version"] = version_config.serialize(new_version, context)
        except MissingValueForSerializationException as e:
            logger.info("Opportunistic finding of new_version failed: %s", e.message)
        except IncompleteVersionRepresentationException as e:
            logger.info("Opportunistic finding of new_version failed: %s", e.message)
        except KeyError as e:
            logger.info("Opportunistic finding of new_version failed")
    return new_version


def _parse_arguments_phase_3(remaining_argv, positionals, defaults, parser2):
    parser3 = argparse.ArgumentParser(
        prog="bumpversion",
        description=DESCRIPTION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        conflict_handler="resolve",
        parents=[parser2],
    )
    parser3.set_defaults(**defaults)
    parser3.add_argument(
        "--current-version",
        metavar="VERSION",
        help="Version that needs to be updated",
        required="current_version" not in defaults,
    )
    parser3.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        default=False,
        help="Don't write any files, just pretend.",
    )
    parser3.add_argument(
        "--new-version",
        metavar="VERSION",
        help="New version that should be in the files",
        required="new_version" not in defaults,
    )
    commitgroup = parser3.add_mutually_exclusive_group()
    commitgroup.add_argument(
        "--commit",
        action="store_true",
        dest="commit",
        help="Commit to version control",
        default=defaults.get("commit", False),
    )
    commitgroup.add_argument(
        "--no-commit",
        action="store_false",
        dest="commit",
        help="Do not commit to version control",
        default=argparse.SUPPRESS,
    )
    taggroup = parser3.add_mutually_exclusive_group()
    taggroup.add_argument(
        "--tag",
        action="store_true",
        dest="tag",
        default=defaults.get("tag", False),
        help="Create a tag in version control",
    )
    taggroup.add_argument(
        "--no-tag",
        action="store_false",
        dest="tag",
        help="Do not create a tag in version control",
        default=argparse.SUPPRESS,
    )
    signtagsgroup = parser3.add_mutually_exclusive_group()
    signtagsgroup.add_argument(
        "--sign-tags",
        action="store_true",
        dest="sign_tags",
        help="Sign tags if created",
        default=defaults.get("sign_tags", False),
    )
    signtagsgroup.add_argument(
        "--no-sign-tags",
        action="store_false",
        dest="sign_tags",
        help="Do not sign tags if created",
        default=argparse.SUPPRESS,
    )
    parser3.add_argument(
        "--tag-name",
        metavar="TAG_NAME",
        help="Tag name (only works with --tag)",
        default=defaults.get("tag_name", "v{new_version}"),
    )
    parser3.add_argument(
        "--tag-message",
        metavar="TAG_MESSAGE",
        dest="tag_message",
        help="Tag message",
        default=defaults.get(
            "tag_message", "Bump version: {current_version} → {new_version}"
        ),
    )
    parser3.add_argument(
        "--message",
        "-m",
        metavar="COMMIT_MSG",
        help="Commit message",
        default=defaults.get(
            "message", "Bump version: {current_version} → {new_version}"
        ),
    )
    parser3.add_argument(
        "--commit-args",
        metavar="COMMIT_ARGS",
        help="Extra arguments to commit command",
        default=defaults.get("commit_args", ""),
    )
    file_names = []
    if "files" in defaults:
        assert defaults["files"] is not None
        file_names = defaults["files"].split(" ")
    parser3.add_argument("part", help="Part of the version to be bumped.")
    parser3.add_argument(
        "files", metavar="file", nargs="*", help="Files to change", default=file_names
    )
    args = parser3.parse_args(remaining_argv + positionals)

    if args.dry_run:
        logger.info("Dry run active, won't touch any files.")

    return args, file_names


def _parse_new_version(args, new_version, vc):
    if args.new_version:
        new_version = vc.parse(args.new_version)
    logger.info("New version will be '%s'", args.new_version)
    return new_version


def _determine_vcs_dirty(possible_vcses, defaults):
    for vcs in possible_vcses:
        if not vcs.is_usable():
            continue

        try:
            vcs.assert_nondirty()
        except WorkingDirectoryIsDirtyException as e:
            if not defaults["allow_dirty"]:
                logger.warning(
                    "%s\n\nUse --allow-dirty to override this if you know what you're doing.",
                    e.message,
                )
                raise

        return vcs

    return None


def _check_files_contain_version(files, current_version, context):
    # make sure files exist and contain version string
    logger.info(
        "Asserting files %s contain the version string...",
        ", ".join([str(f) for f in files]),
    )
    for f in files:
        f.should_contain_version(current_version, context)


def _replace_version_in_files(files, current_version, new_version, dry_run, context):
    # change version string in files
    for f in files:
        f.replace(current_version, new_version, context, dry_run)


def _log_list(config, new_version):
    config.set("bumpversion", "new_version", new_version)
    for key, value in config.items("bumpversion"):
        logger_list.info("%s=%s", key, value)
    config.remove_option("bumpversion", "new_version")


def _update_config_file(
        config, config_file, config_newlines, config_file_exists, new_version, dry_run,
):
    config.set("bumpversion", "current_version", new_version)
    new_config = io.StringIO()
    try:
        write_to_config_file = (not dry_run) and config_file_exists

        logger.info(
            "%s to config file %s:",
            "Would write" if not write_to_config_file else "Writing",
            config_file,
        )

        config.write(new_config)
        logger.info(new_config.getvalue())

        if write_to_config_file:
            with open(config_file, "wt", encoding="utf-8", newline=config_newlines) as f:
                f.write(new_config.getvalue().strip() + "\n")

    except UnicodeEncodeError:
        warnings.warn(
            "Unable to write UTF-8 to config file, because of an old configparser version. "
            "Update with `pip install --upgrade configparser`."
        )


def _commit_to_vcs(files, context, config_file, config_file_exists, vcs, args,
                   current_version, new_version):
    commit_files = [f.path for f in files]
    if config_file_exists:
        commit_files.append(config_file)
    assert vcs.is_usable(), "Did find '{}' unusable, unable to commit.".format(
        vcs.__name__
    )
    do_commit = args.commit and not args.dry_run
    logger.info(
        "%s %s commit",
        "Would prepare" if not do_commit else "Preparing",
        vcs.__name__,
    )
    for path in commit_files:
        logger.info(
            "%s changes in file '%s' to %s",
            "Would add" if not do_commit else "Adding",
            path,
            vcs.__name__,
        )

        if do_commit:
            vcs.add_path(path)

    context = {
        "current_version": args.current_version,
        "new_version": args.new_version,
    }
    context.update(time_context)
    context.update(prefixed_environ())
    context.update({'current_' + part: current_version[part].value for part in current_version})
    context.update({'new_' + part: new_version[part].value for part in new_version})

    commit_message = args.message.format(**context)

    logger.info(
        "%s to %s with message '%s'",
        "Would commit" if not do_commit else "Committing",
        vcs.__name__,
        commit_message,
    )
    if do_commit:
        vcs.commit(
            message=commit_message,
            context=context,
            extra_args=[arg.strip() for arg in args.commit_args.splitlines()],
        )
    return context


def _tag_in_vcs(vcs, context, args):
    sign_tags = args.sign_tags
    tag_name = args.tag_name.format(**context)
    tag_message = args.tag_message.format(**context)
    do_tag = args.tag and not args.dry_run
    logger.info(
        "%s '%s' %s in %s and %s",
        "Would tag" if not do_tag else "Tagging",
        tag_name,
        "with message '{}'".format(tag_message) if tag_message else "without message",
        vcs.__name__,
        "signing" if sign_tags else "not signing",
    )
    if do_tag:
        vcs.tag(sign_tags, tag_name, tag_message)
