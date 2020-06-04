import logging as log
import sys
from git import Repo, Actor, InvalidGitRepositoryError, NoSuchPathError
from github import Github, GithubException, BadCredentialsException, RateLimitExceededException, UnknownObjectException
from constants import GIT_AUTHOR, GIT_AUTHOR_EMAIL, GIT_COMMITTER, GIT_COMMITTER_EMAIL
from tracker import TranslationTracker
from updater import GithubUpdater, GitUpdater, UpdaterTemplate
from constants import RFC5646_LANGUAGE_TAGS
import re
import templates
import traceback
import argparse
import json
from pathlib import Path


def arg_repo(string):
    """
    Define a local git repository, whose path is a given parameter.

    :param string: the path to local git repo
    :return: corresponding Repo object
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
    Define a tag:path string format type and returns the tuple (tag, path).

    :param string: the value to parse as tag:path
    :return: the converted tuple (tag, path)
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


def arg_github(repo_str, token_str):
    """
    Define a Github repository argument with the access token of a Github App installed on the repository.

    :param repo_str: the Github repository formatted like 'Owner/Repository'
    :param token_str: the access token with enough permission
    :return: the Repository object
    :raise argparse.ArgumentTypeError: when access token is a bad credential
    :raise argparse.ArgumentTypeError: when Github rate limit is reached
    :raise argparse.ArgumentTypeError: when the repository is not found (either doesn't exist or authent App doesn't have access)
    :raise argparse.ArgumentTypeError: when some other github exception occurs
    """
    try:
        g = Github(token_str)
        github_repo = g.get_repo(repo_str)
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
    return github_repo


def arg_branch(string):
    """
    Define a valid branch name argument using regex.

    :param string: the branch name
    :return: string
    :raise argparse.ArgumentTypeError: when string doesn't match a branch name
    """
    # seen here https://stackoverflow.com/a/12093994
    BRANCH_PATTERN = r"^(?!@$|/|.*([/.]\.|//|@\{|\\))[^\000-\037\177 ~^:?*[]+/[^\000-\037\177 ~^:?*[]+(?<!\.lock|[/.])$"
    if re.match(BRANCH_PATTERN, string):
        return string
    else:
        msg = "{} is not a valid branch name".format(string)
        raise argparse.ArgumentTypeError(msg)


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
    gen_group.add_argument('--branch-gen', dest='gen_branch', action='store',
                           type=arg_branch, metavar='BRANCH',
                           help="branch to commit generated files")
    gen_group.add_argument('--gen-stubs', dest='gen_stubs', action='store',
                           type=str, nargs='+', metavar='FNMATCH',
                           help="fnmatch patterns for missing translation files to generate stubs")
    gen_group.add_argument('--stub-commit', dest='stub_commit', action='store',
                           type=str, default='Generated stubs', metavar='MSG',
                           help="commit message for stub creation")
    gen_group.add_argument('--stub-template', dest='stub_template', action='store',
                           type=UpdaterTemplate, default='Translation has not been done yet.', metavar='TEMPLATE',
                           help="template for stub file content")
    gen_group.add_argument('--gen-copy', dest='gen_copy', action='store',
                           type=str, nargs='+', metavar='FNMATCH',
                           help="fnmatch patterns for missing translation files to copy from original")
    gen_group.add_argument('--copy-commit', dest='copy_commit', action='store',
                           type=str, default='Generated copies', metavar='MSG',
                           help="commit message for copy generation")
    # Instructing args
    instruct_group = parser.add_argument_group('instructing', 'Instruct translators according to backtracking and auto generation')
    instruct_group.add_argument('--github', dest='github_repo', action='store',
                                type=arg_github, nargs=2, metavar=('REPO', 'TOKEN'),
                                help="github such as 'Owner/Repo' with access token")
    instruct_group.add_argument('--request-merge', dest='request_merge', action='store_true',
                                help="make a Pull Request to merge branch-gen if different than active branch and files were generated")
    instruct_group.add_argument('--instruct-issues', dest='instruct_issues', action='store',
                                type=str, nargs='+', metavar='GLOB',
                                help="fnmatch patterns matching translation files to instruct in Issues")
    instruct_group.add_argument('--issue-label', dest='issue_label', action='store',
                                type=str, default='translation-update', metavar='LABEL',
                                help="label to identify instructing issues")
    instruct_group.add_argument('--issue-title-template', dest='issue_title_template', action='store',
                                type=UpdaterTemplate, default='{t.status}: {t.translation_path}', metavar='TEMPLATE',
                                help="template for issue title (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--issue-create-template', dest='issue_create_template', action='store',
                                type=UpdaterTemplate, default='', metavar='TEMPLATE',
                                help="template for \"To Create\" translation file instructions in issue body")
    instruct_group.add_argument('--issue-initialize-template', dest='issue_initialize_template', action='store',
                                type=UpdaterTemplate, default='', metavar='TEMPLATE',
                                help="template for \"To Initialize\" translation file instructions in issue body")
    instruct_group.add_argument('--issue-update-template', dest='issue_update_template', action='store',
                                type=UpdaterTemplate, default='', metavar='TEMPLATE',
                                help="template for \"To Update\" translation file instructions in issue body")
    instruct_group.add_argument('--issue-uptodate-template', dest='issue_uptodate_template', action='store',
                                type=UpdaterTemplate, default='', metavar='TEMPLATE',
                                help="template for \"Up-To-Date\" translation file instructions in issue body")
    instruct_group.add_argument('--issue-orphan-template', dest='issue_orphan_template', action='store',
                                type=UpdaterTemplate, default='', metavar='TEMPLATE',
                                help="template for \"Orphan\" translation file instructions in issue body")
    instruct_group.add_argument('--instruct-projects', dest='instruct_projects', action='store',
                                type=str, nargs='+', metavar='GLOB',
                                help="fnmatch patterns matching translation files to instruct in Projects")
    instruct_group.add_argument('--project-title-template', dest='project_title_templat', action='store',
                                type=UpdaterTemplate, default='{t.language} translation', metavar='TEMPLATE',
                                help="template for project title")
    instruct_group.add_argument('--project-description-template', dest='project_description_template', action='store',
                                type=UpdaterTemplate, default='', metavar='TEMPLATE',
                                help="template for project description, only relevant at project creation")
    instruct_group.add_argument('--project-column-create-template', dest='project_column_create_template', action='store',
                                type=UpdaterTemplate, default='To Create', metavar='TEMPLATE',
                                help="template for \"To Create\" translation files column name")
    instruct_group.add_argument('--project-column-initialize-template', dest='project_column_initialize_template', action='store',
                                type=UpdaterTemplate, default='To Initialize', metavar='TEMPLATE',
                                help="template for \"To Initialize\" translation files column name")
    instruct_group.add_argument('--project-column-update-template', dest='project_column_update_template', action='store',
                                type=UpdaterTemplate, default='To Update', metavar='TEMPLATE',
                                help="template for \"To Update\" translation files column name")
    instruct_group.add_argument('--project-column-uptodate-template', dest='project_column_uptodate_template', action='store',
                                type=UpdaterTemplate, default='Up-To-Date', metavar='TEMPLATE',
                                help="template for \"Up-To-Date\" translation files column name")
    instruct_group.add_argument('--project-column-orphan-template', dest='project_column_orphan_template', action='store',
                                type=UpdaterTemplate, default='Orphans', metavar='TEMPLATE',
                                help="template for \"Orphan\" translation files column name")
    instruct_group.add_argument('--project-card-create-template', dest='project_card_create_template', action='store',
                                type=UpdaterTemplate, default='{t.translation_path}', metavar='TEMPLATE',
                                help="template for instructions about \"To Create\" translation files, in project column card (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--project-card-initialize-template', dest='project_card_initialize_template', action='store',
                                type=UpdaterTemplate, default='{t.translation_path}', metavar='TEMPLATE',
                                help="template for instructions about \"To Initialize\" translation files, in project column card (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--project-card-update-template', dest='project_card_update_template', action='store',
                                type=UpdaterTemplate, default='{t.translation_path}', metavar='TEMPLATE',
                                help="template for instructions about \"To Update\" translation files, in project column card (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--project-card-uptodate-template', dest='project_card_uptodate_template', action='store',
                                type=UpdaterTemplate, default='{t.translation_path}', metavar='TEMPLATE',
                                help="template for instructions about \"Up-To-Date\" translation files, in project column card (must be unique, using {t.translation_path})")
    instruct_group.add_argument('--project-card-orphan-template', dest='project_card_orphan_template', action='store',
                                type=UpdaterTemplate, default='{t.translation_path}', metavar='TEMPLATE',
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
        ignore = args.ignore + [path for tag, path in args.translations]
        for tag, path in args.translations:
            tracker.put(path, args.original, tag, ignore=ignore, filter=args.filter)

        # TRACKING changes
        log.info("Started tracking given translation files.")
        tracks = tracker.track()
        log.info("Finished tracking given translation files.")

        # GENERATING inexistent pages
        if args.gen_stubs:
            creator = GitUpdater(tracks, args.git_repo, Actor(GIT_COMMITTER, GIT_COMMITTER_EMAIL), Actor(GIT_AUTHOR, GIT_AUTHOR_EMAIL))
            log.info("Started creating stubs.")
            creator.create_stubs(templates.STUB_COMMIT_MSG, templates.STUB_FILE_CONTENT)
            log.info("Finished updating stub TBC files.")

        # UPDATING Issues / Projects
        try:
            updater = GithubUpdater(tracks, args.github_repo)
            if args.request_merge:
                # TODO make PR
                pass
            if args.instruct_issues:
                log.info("Started updating issues on Github.")

                open_issues = updater.update_issues(fnmatches=args.instruct_issues,
                                                    bot_label=args.issue_label,
                                                    title_template=args.issue_title_template,
                                                    tbc_template=args.issue_create_template,
                                                    tbi_template=args.issue_initialize_template,
                                                    update_template=args.issue_update_template,
                                                    utd_template=args.issue_uptodate_template,
                                                    orphan_template=args.issue_orphan_template)
                log.info("Finished updating issues on Github.")
            if args.instruct_projects:
                log.info("Started updating Projects on Github.")

                updater.update_projects(fnmatches=args.instruct_projects,
                                        title_template=args.project_title_template,
                                        body_template=args.project_body_template,
                                        tbc_column_template=args.project_column_create_template,
                                        tbi_column_template=args.project_column_initialize_template,
                                        update_column_template=args.project_column_update_template,
                                        utd_column_template=args.project_column_uptodate_template,
                                        orphan_column_template=args.project_column_orphan_template,
                                        tbc_card_template=args.project_card_create_template,
                                        tbi_card_template=args.project_card_initialize_template,
                                        update_card_template=args.project_card_update_template,
                                        utd_card_template=args.project_card_uptodate_template,
                                        orphan_card_template=args.project_card_orphan_template)

                log.info("Finished updating Projects on Github.")
        except RateLimitExceededException as e:
            log.critical("Github rate limit exceeded in the middle of the job, exiting (maybe wait a bit to redo?)")
            log.debug("Github rate limit exceeded: {}".format(str(e)))
            exit(1)
        except UnknownObjectException as e:
            log.critical("Got 404 HTTP error, the given token might not have the required permissions. Exiting.")
            log.debug("Github unknown object exception: {}".format(str(e)))
            exit(1)
        except GithubException as e:
            log.critical("Got an unexpected Github API exception, exiting.")
            log.debug("Unexpected Github exception: {}".format(str(e)))
            exit(1)

        out_status = ','.join(["{}:{}".format(t.translation.path, t.status) for t in tracks])
        json.dump(tracks, args.output)

    except Exception:
        log.critical("Got an unexpected error, exiting.")
        log.debug("Unexpected exception: {}".format(traceback.format_exc()))
        exit(1)
