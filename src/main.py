import logging as log
import sys
from git import (
    Repo,
    Actor,
    InvalidGitRepositoryError,
    NoSuchPathError
)
from github import (
    Github,
    GithubException,
    BadCredentialsException,
    RateLimitExceededException,
    UnknownObjectException
)
from constants import RFC5646_LANGUAGE_TAGS
from tracker import (
    TranslationTracker,
    Status
)
from model import (
    TranslationTrackModel,
    StubTemplate,
    GithubTemplate,
    GithubTemplater
)
from generator import GitUpdater
from instructor import (
    IssuesInstructor,
    ProjectsInstructor
)

import traceback
import argparse
import json
from pathlib import Path


def arg_repo(string):
    """
    Defines a local git repository, whose path is a given parameter.

    :param str string: the path to local git repo
    :return: corresponding Repo object
    :rtype: git.Repo
    :raise argparse.ArgumentTypeError: when string doesn't lead to an existing path
    :raise argparse.ArgumentTypeError: when string leads to an invalid git repository
    """
    try:
        return Repo(string)
    except NoSuchPathError:
        msg = "path {} doesn't exist".format(string)
        raise argparse.ArgumentTypeError(msg)
    except InvalidGitRepositoryError:
        msg = "path {} leads to an invalid git repository".format(string)
        raise argparse.ArgumentTypeError(msg)


def arg_tag_path(string):
    """
    Defines a tag:path string format type and returns the tuple (tag, path).

    :param str string: the value to parse as tag:path
    :return: the converted tuple (tag, path)
    :rtype: tuple(str, str)
    :raise argparse.ArgumentTypeError: when it's not formatted correctly
    :raise argparse.ArgumentTypeError: when tag is not a valid RFC 5646 language tag
    """
    try:
        i = string.index(':')
    except ValueError:
        msg = "{} is not tag:path".format(string)
        raise argparse.ArgumentTypeError(msg)
    tag = string[:i]
    if tag not in RFC5646_LANGUAGE_TAGS.keys():
        msg = "{} is not a valid RFC 5646 language tag".format(tag)
        raise argparse.ArgumentTypeError(msg)
    path = Path(string[i + 1:])
    return (tag, path)


class GithubArg(argparse.Action):
    """
    Defines a Github repository argument with the access token of a Github App installed on the repository.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        """
        This argparse action sets the github_repo argument, instance of ``github.Repository.Repository``, in the namespace from both repository value and an associated access token.

        :param argparse.ArgumentParser parser: the parser
        :param argparse.Namespace namespace: namespace which will be returned by argparse
        :param values: 2 values list, the first contains the Github repository formatted like 'Owner/Repository', the second is the access token
        :type values: list(str)
        :param option_string: unused value
        :raise argparse.ArgumentTypeError: when access token is a bad credential
        :raise argparse.ArgumentTypeError: when Github rate limit is reached
        :raise argparse.ArgumentTypeError: when the repository is not found (either doesn't exist or authent App doesn't have access)
        :raise argparse.ArgumentTypeError: when some other github exception occurs
        """
        repo_str = values[0]
        token_str = values[1]
        try:
            g = Github(token_str)
            namespace.github_repo = g.get_repo(repo_str)
        except BadCredentialsException:
            msg = "authentication with access token didn't work"
            raise argparse.ArgumentTypeError(msg)
        except RateLimitExceededException:
            msg = "Github rate limit exceeded, maybe wait a bit"
            raise argparse.ArgumentTypeError(msg)
        except UnknownObjectException:
            msg = "unknown repo {}, check the spelling and check the Github App is installed on the repository".format(repo_str)
            raise argparse.ArgumentTypeError(msg)
        except GithubException:
            msg = "Github exception occured: {}".format(traceback.format_exc())
            raise argparse.ArgumentTypeError(msg)


def ActorArg(dest):
    """
    Factory for an Actor argument. Specify the destination to ``argparse.Namespace`` and get the ``argparse.Action`` argument definer.

    :param str dest: the attribute destination in the namespace to hold the Actor after the action is called when parsing args
    :return: the action class
    :rtype: ActorArgClass
    """
    class ActorArgClass(argparse.Action):
        """
        Defines an ``github.Actor`` argument to pass through arparse.
        """
        def __call__(self, parser, namespace, values, option_string=None):
            """
            This argparse action sets the ``dest`` str attribute as an ``github.Actor`` in the namespace from a name and an e-mail as values.

            :param argparse.ArgumentParser parser: the parser
            :param argparse.Namespace namespace: namespace which will be returned by argparse
            :param values: 2 values list, the first contains the name of the actor, the second is the email address
            :type values: list(str)
            :param option_string: unused value
            """
            name = values[0]
            email = values[1]
            namespace.__setattr__(dest, Actor(name, email))

    return ActorArgClass


def arg_stub_template_file(string):
    """
    Defines a valid stub template containing file (utf-8 encoded).

    :param str string: the filename to read
    :return: template, content of file
    :rtype: StubTemplate
    :raise argparse.ArgumentTypeError: when given file doesn't exist
    :raise argparse.ArgumentTypeError: when given couldn't be opened
    """
    try:
        with open(string, 'r', encoding='UTF-8') as f:
            return StubTemplate(f.read())
    except FileNotFoundError:
        msg = "{} file doesn't exist".format(string)
        raise argparse.ArgumentTypeError(msg)
    except IOError:
        msg = "could not read file {}".format(string)
        raise argparse.ArgumentTypeError(msg)


def arg_github_template_file(string):
    """
    Defines a valid github template containing file (utf-8 encoded).

    :param str string: the filename to read
    :return: template, content of file
    :rtype: StubTemplate
    :raise argparse.ArgumentTypeError: when given file doesn't exist
    :raise argparse.ArgumentTypeError: when given couldn't be opened
    """
    try:
        with open(string, 'r', encoding='UTF-8') as f:
            return GithubTemplate(f.read())
    except FileNotFoundError:
        msg = "{} file doesn't exist".format(string)
        raise argparse.ArgumentTypeError(msg)
    except IOError:
        msg = "could not read file {}".format(string)
        raise argparse.ArgumentTypeError(msg)


def make_templater(map):
    """
    Create a GithubTemplater from a dict mapping status as key and template as value.
    When a template is empty, it is not provided to the templater.

    :param map: the dictionary
    :type map: dict(tracker.Status, model.GithubTemplate)
    :return: the templater
    :rtype: model.GithubTemplater
    """
    templater = GithubTemplater()
    for (status, template) in map.items():
        if not template.empty:
            templater[status] = template

    return templater


if __name__ == '__main__':
    logformat = "[%(asctime)s][%(levelname)s] %(message)s"
    log.basicConfig(level=log.INFO, format=logformat)

    LOGGER_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]

    parser = argparse.ArgumentParser(description="Backtrack changes in a git repository original localised files to report on their equivalent translation files")

    # General and backtracking args
    parser.add_argument('--log-level', '-l', dest='loglvl', action='store',
                        type=str, choices=LOGGER_LEVELS, default="INFO", metavar='LOGLVL',
                        help="set logging level")
    parser.add_argument('--repo', '-r', dest='git_repo', action='store',
                        type=arg_repo, default='.', metavar='PATH',
                        help="local git repository path")
    parser.add_argument('original', action='store',
                        type=Path, metavar='ORIGINAL_PATH',
                        help="original files path, relative to 'repo'")
    parser.add_argument('translations', action='store',
                        type=arg_tag_path, nargs='+', metavar='LANGTAG:TRANSLATION_PATH',
                        help="language tags & path patterns matching translation files, relative to 'repo'")
    parser.add_argument('--filter', '-f', dest='filter', action='store',
                        type=str, default='**', nargs='+', metavar='GLOB',
                        help="glob patterns to filter matching files, relative to 'original' and 'translations'")
    parser.add_argument('--ignore', '-i', dest='ignore', action='store',
                        type=str, default='', nargs='+', metavar='GLOB',
                        help="glob patterns to ignore matching files, relative to 'original' and 'translations'")
    parser.add_argument('--output', '-o', dest='output', action='store',
                        type=argparse.FileType('w'), default=sys.stdout, metavar='FILE',
                        help="output file")
    # Auto generation args
    gen_group = parser.add_argument_group("auto generation", "Auto generate files according to backtracking")
    gen_group.add_argument('--gen-branch', dest='gen_branch', action='store',
                           type=str, metavar='BRANCH',
                           help="branch to commit generated files")
    gen_group.add_argument('--request-merge', dest='request_merge', action='store_true',
                           help="make a Pull Request to merge gen-branch if different than active branch and files were generated")
    gen_group.add_argument('--gen-committer', dest='gen_committer', action=ActorArg("gen_committer"),
                           type=str, default=Actor('bot', 'bot@example.com'), nargs=2, metavar=('NAME', 'EMAIL'),
                           help="committer defined when committing generated files")
    gen_group.add_argument('--gen-author', dest='gen_author', action=ActorArg("gen_author"),
                           type=str, default=Actor('bot', 'bot@example.com'), nargs=2, metavar=('NAME', 'EMAIL'),
                           help="author defined when committing generated files")
    gen_group.add_argument('--gen-stubs', dest='gen_stubs', action='store',
                           type=str, nargs='+', metavar='FNMATCH',
                           help="fnmatch patterns for missing translation files to generate stubs")
    gen_group.add_argument('--stub-commit', dest='stub_commit', action='store',
                           type=str, default='Generated stubs', metavar='MSG',
                           help="commit message for stub creation")
    gen_group.add_argument('--stub-template', dest='stub_template', action='store',
                           type=arg_stub_template_file, default=StubTemplate('Translation has not been done yet.'), metavar='TEMPLATE FILE',
                           help="template for stub file content")
    gen_group.add_argument('--gen-copy', dest='gen_copy', action='store',
                           type=str, nargs='+', metavar='FNMATCH',
                           help="fnmatch patterns for missing translation files to copy from original")
    gen_group.add_argument('--copy-commit', dest='copy_commit', action='store',
                           type=str, default='Generated copies', metavar='MSG',
                           help="commit message for copy generation")
    # Instructing args
    instruct_group = parser.add_argument_group('instructing', 'Instruct translators according to backtracking and auto generation')
    instruct_group.add_argument('--github', dest='github_repo', action=GithubArg,
                                type=str, nargs=2, metavar=('REPO', 'TOKEN'),
                                help="github repo such as 'Owner/Repo' with access token")
    instruct_group.add_argument('--instruct-issues', dest='instruct_issues', action='store',
                                type=str, nargs='+', metavar='FNMATCH',
                                help="fnmatch patterns matching translation files to instruct in Issues")
    instruct_group.add_argument('--issue-label', dest='issue_label', action='store',
                                type=str, default='translation-update', metavar='LABEL',
                                help="label to identify instructing issues")
    instruct_group.add_argument('--issue-title-template', dest='issue_title_template', action='store',
                                type=GithubTemplate, default='{t.status}: {t.translation.path}', metavar='INLINE TEMPLATE',
                                help="template for issue title (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--issue-create-template', dest='issue_create_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for \"To Create\" translation file instructions in issue body")
    instruct_group.add_argument('--issue-initialize-template', dest='issue_initialize_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for \"To Initialize\" translation file instructions in issue body")
    instruct_group.add_argument('--issue-update-template', dest='issue_update_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for \"To Update\" translation file instructions in issue body")
    instruct_group.add_argument('--issue-uptodate-template', dest='issue_uptodate_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for \"Up-To-Date\" translation file instructions in issue body")
    instruct_group.add_argument('--issue-orphan-template', dest='issue_orphan_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for \"Orphan\" translation file instructions in issue body")
    instruct_group.add_argument('--instruct-projects', dest='instruct_projects', action='store',
                                type=str, nargs='+', metavar='FNMATCH',
                                help="fnmatch patterns matching translation files to instruct in Projects")
    instruct_group.add_argument('--project-title-template', dest='project_title_template', action='store',
                                type=GithubTemplate, default='{t.language} translation', metavar='INLINE TEMPLATE',
                                help="template for project title")
    instruct_group.add_argument('--project-description-template', dest='project_description_template', action='store',
                                type=GithubTemplate, default='', metavar='INLINE TEMPLATE',
                                help="template for project description, only relevant at project creation")
    instruct_group.add_argument('--project-column-create-template', dest='project_column_create_template', action='store',
                                type=GithubTemplate, default='To Create', metavar='INLINE TEMPLATE',
                                help="template for \"To Create\" translation files column name")
    instruct_group.add_argument('--project-column-initialize-template', dest='project_column_initialize_template', action='store',
                                type=GithubTemplate, default='To Initialize', metavar='INLINE TEMPLATE',
                                help="template for \"To Initialize\" translation files column name")
    instruct_group.add_argument('--project-column-update-template', dest='project_column_update_template', action='store',
                                type=GithubTemplate, default='To Update', metavar='INLINE TEMPLATE',
                                help="template for \"To Update\" translation files column name")
    instruct_group.add_argument('--project-column-uptodate-template', dest='project_column_uptodate_template', action='store',
                                type=GithubTemplate, default='Up-To-Date', metavar='INLINE TEMPLATE',
                                help="template for \"Up-To-Date\" translation files column name")
    instruct_group.add_argument('--project-column-orphan-template', dest='project_column_orphan_template', action='store',
                                type=GithubTemplate, default='Orphans', metavar='INLINE TEMPLATE',
                                help="template for \"Orphan\" translation files column name")
    instruct_group.add_argument('--project-card-create-template', dest='project_card_create_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for instructions about \"To Create\" translation files, in project column card (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--project-card-initialize-template', dest='project_card_initialize_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for instructions about \"To Initialize\" translation files, in project column card (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--project-card-update-template', dest='project_card_update_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for instructions about \"To Update\" translation files, in project column card (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--project-card-uptodate-template', dest='project_card_uptodate_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for instructions about \"Up-To-Date\" translation files, in project column card (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--project-card-orphan-template', dest='project_card_orphan_template', action='store',
                                type=arg_github_template_file, default=GithubTemplate(''), metavar='TEMPLATE FILE',
                                help="template for instructions about \"Orphan\" translation files, in project column card (must be unique, using {t.translation_path})")

    args = parser.parse_args()

    # manual parsing for interdependent arguments
    if args.instruct_issues:
        if not args.github_repo:
            log.error("No Github repository given: can't instruct via Issues.")
            exit(1)
        elif not args.github_repo.has_issues:
            log.error("Issues is NOT enabled on Github Repository: can't instruct via Issues.")
            exit(1)
    if args.instruct_projects and not args.github_repo.has_projects:
        if not args.github_repo:
            log.error("No Github repository given: can't instruct via Projects")
            exit(1)
        elif not args.github_repo.has_projects:
            log.error("Projects is NOT enabled on Github Repository: can't instruct via Projects.")
            exit(1)

    try:
        # set chosen log level
        log.getLogger().setLevel(args.loglvl)

        # create tracker
        tracker = TranslationTracker(args.git_repo)
        ignore = args.ignore + ["{}/**/*".format(path.as_posix()) for tag, path in args.translations]
        for tag, path in args.translations:
            tracker.put(path, args.original, tag, original_ignore_globs=ignore, filter_globs=args.filter)

        # TRACKING changes
        log.info("Started tracking given translation files.")
        tracks = tracker.track()
        log.info("Finished tracking given translation files.")

        # GENERATING inexistent pages
        if args.gen_branch:
            branch = args.gen_branch
        else:
            branch = args.git_repo.active_branch.name

        gitter = GitUpdater(tracks, args.git_repo, args.gen_committer, args.gen_author, branch)

        if args.gen_stubs:
            log.info("Started creating stubs for To Create translations.")
            gitter.create_stubs(args.stub_commit, args.stub_template, args.gen_stubs)
            log.info("Finished updating stub files.")

        if args.gen_copy:
            log.info("Started copying original files to translation files for To Create translations.")
            gitter.create_copies(args.copy_commit, args.gen_copy)
            log.info("Finished copying original files to translation files.")

        if args.request_merge:
            gitter.finish(pull_request=args.github_repo, force_push=True)
        else:
            gitter.finish(force_push=True)

        # INSTRUCTING Issues / Projects
        if args.instruct_issues:
            body_templater = make_templater({
                Status.TBC: args.issue_create_template,
                Status.TBI: args.issue_initialize_template,
                Status.Update: args.issue_update_template,
                Status.UTD: args.issue_uptodate_template,
                Status.Orphan: args.issue_orphan_template
            })
            issuer = IssuesInstructor(tracks=tracks,
                                      repo=args.github_repo,
                                      label=args.issue_label,
                                      title_template=args.issue_title_template,
                                      body_templater=body_templater
                                      )
            log.info("Started instructing in GitHub Issues.")

            open_issues = issuer.instruct(filters=args.instruct_issues)

            log.info("Finished instructing in GitHub Issues.")
        if args.instruct_projects:
            column_templater = make_templater({
                Status.TBC: args.project_column_create_template,
                Status.TBI: args.project_column_initialize_template,
                Status.Update: args.project_column_update_template,
                Status.UTD: args.project_column_uptodate_template,
                Status.Orphan: args.project_column_orphan_template
            })
            card_templater = make_templater({
                Status.TBC: args.project_card_create_template,
                Status.TBI: args.project_card_initialize_template,
                Status.Update: args.project_card_update_template,
                Status.UTD: args.project_card_uptodate_template,
                Status.Orphan: args.project_card_orphan_template
            })
            projector = ProjectsInstructor(tracks=tracks,
                                           repo=args.github_repo,
                                           title_template=args.project_title_template,
                                           column_templater=column_templater,
                                           card_templater=card_templater,
                                           body_template=args.project_description_template)
            log.info("Started instructing in GitHub Projects.")

            projector.instruct(filters=args.instruct_projects)

            log.info("Finished instructing in GitHub Projects.")

        out_status = ','.join(["{}:{}".format(t.translation.path, t.status) for t in tracks])
        json.dump([TranslationTrackModel(t) for t in tracks], args.output, default=lambda o: o.__dict__, separators=(',', ':'))

    except RateLimitExceededException as e:
        log.critical("Github rate limit exceeded in the middle of the job, exiting (maybe wait a bit to redo?)")
        log.debug("Github rate limit exceeded: {}".format(str(e)))
        exit(1)
    except GithubException as e:
        log.critical("Got an unexpected Github API exception, exiting.")
        log.debug("Unexpected Github exception: {}".format(str(e)))
        exit(1)
    except Exception:
        log.critical("Got an unexpected error, exiting.")
        log.debug("Unexpected exception: {}".format(traceback.format_exc()))
        exit(1)
