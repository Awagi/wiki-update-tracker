import logging as log
import sys
from git import Repo, Actor, InvalidGitRepositoryError, NoSuchPathError
from github import Github, GithubException, BadCredentialsException, RateLimitExceededException, UnknownObjectException
from constants import GIT_AUTHOR, GIT_AUTHOR_EMAIL, GIT_COMMITTER, GIT_COMMITTER_EMAIL
from tracker import TranslationTracker, SamePathException, LanguageTagException, Status
from updater import GithubUpdater, GitUpdater
import templates
import traceback


if __name__ == '__main__':
    try:
        logformat = "[%(asctime)s][%(levelname)s] %(message)s"
        log.basicConfig(level=log.INFO, format=logformat)

        BOOLEAN_TRUE_ARGV = ['1', 'true', 't', 'yes', 'y']
        BOOLEAN_FALSE_ARGV = ['0', 'false', 'f', 'no', 'n']

        # Launch the script with below args, and from the git repo directory
        # expected args:
        # 0: script name...
        # 1: git repo system path (e.g '.')
        # 2: original file or directory path, relative to the git repo (e.g 'wiki/en')
        # 3: ignored files relative paths (e.g 'wiki/LICENSE,wiki/.vuepress')
        # 4: translations with codes map to the file paths, relative to the git repo (e.g 'fr:wiki/fr,de:wiki/de')
        # 5: file suffix
        # 6: Github repo ('author/repo')
        # 7: Issues bot label
        # 8: token for Github authent
        # 9: log level ('DEBUG', 'INFO', 'WARNING' or 'CRITICAL')
        # 10: auto create enabled ('0' for disabled, '1' for enabled)
        # 11: set issues ('0' for disabled, '1' for enabled)
        # 12: set projects ('0' for disabled, '1' for enabled)
        if len(sys.argv) < 13:
            log.critical("Can't operate without params.")
            exit(1)

        log.getLogger().setLevel(sys.argv[9])

        repo_path = sys.argv[1]
        original_path = sys.argv[2]
        ignored_paths = sys.argv[3]
        translations = sys.argv[4]
        file_suffix = sys.argv[5]
        repo = sys.argv[6]
        bot_label = sys.argv[7]
        token = sys.argv[8]
        auto_create = sys.argv[10]
        top_issues = sys.argv[11]
        top_projects = sys.argv[12]

        # CHECKING system inputs
        try:
            # check Git repo path
            try:
                sys_repo = Repo(repo_path)
            except NoSuchPathError:
                raise ValueError("git repo path is incorrect")
            except InvalidGitRepositoryError:
                raise ValueError("git repo at repo path is invalid")

            tracker = TranslationTracker(sys_repo)

            # parse ignored_paths
            if len(ignored_paths) == 0:
                ignored_paths = []
            else:
                ignored_paths = ignored_paths.split(',')

            # check original path and translation paths and codes
            try:
                tag_paths = [tag_path.split(':') for tag_path in translations.split(',')]
            except IndexError:
                raise ValueError("translations with language tags + paths not formatted correctly")
            ignored_paths.extend([path for tag, path in tag_paths])
            if len(translations) != 0:
                for tag, path in tag_paths:
                    try:
                        # map translation dirs / files to their original equivalent dir / file
                        tracker.put(path, original_path, tag, ignore=ignored_paths, suffixes=[file_suffix])
                    except SamePathException:
                        raise ValueError("translation paths can't be the same as original path")
                    except ValueError:
                        raise ValueError("original not found, make sure it's a relative path based on the git repository")
                    except LanguageTagException:
                        raise ValueError("given language tag is not correct, use defined tags in RFC 5646")

            # check auto_create value
            if auto_create in BOOLEAN_TRUE_ARGV:
                auto_create = True
            elif auto_create in BOOLEAN_FALSE_ARGV:
                auto_create = False
            else:
                raise ValueError("auto_create not acceptable, please check its value")
            # check top_issues value
            if top_issues in BOOLEAN_TRUE_ARGV:
                top_issues = True
            elif top_issues in BOOLEAN_FALSE_ARGV:
                top_issues = False
            else:
                raise ValueError("top_issues not acceptable, please check its value")
            # check top_projects value
            if top_projects in BOOLEAN_TRUE_ARGV:
                top_projects = True
            elif top_projects in BOOLEAN_FALSE_ARGV:
                top_projects = False
            else:
                raise ValueError("top_projects not acceptable, please check its value")
        except ValueError as e:
            log.critical("Inputs are incorrect.")
            log.debug("Error: {}".format(str(e)))
            exit(1)

        # CHECKING Github inputs
        try:
            g = Github(token)
            github_repo = g.get_repo(repo)
        except BadCredentialsException as e:
            log.critical("Given Github credentials don't work, can't do job, exiting.")
            log.debug("Github bad credentials: {}".format(str(e)))
            exit(1)
        except RateLimitExceededException as e:
            log.critical("Github rate limit exceeded, can't do job right now, exiting (maybe wait a bit then restart).")
            log.debug("Github rate limit exceeded: {}".format(str(e)))
            exit(1)
        except UnknownObjectException as e:
            if top_issues or top_projects:
                log.warning("Got 404 HTTP exception, repository probably doesn't exist. Script will continue but won't update issues nor projects.")
                log.debug("Github unknown object exception: {}".format(str(e)))
                top_issues = False
                top_projects = False
        except GithubException as e:
            log.critical("Got an unexpected Github API exception, exiting.")
            log.debug("Unexpected Github Exception: {}".format(str(e)))
            exit(1)

        if top_issues and not github_repo.has_issues:
            log.warning("Won't update Issues: given repository doesn't have Issues enabled.")
        if top_projects and not github_repo.has_projects:
            log.warning("Won't update Projects: given repository doesn't have Projects enabled.")

        # TRACKING changes
        log.info("Started tracking given translation files.")
        tracks = tracker.track()
        log.info("Finished tracking given translation files.")

        # CREATING inexistent pages
        if auto_create:
            creator = GitUpdater(tracks, sys_repo, Actor(GIT_COMMITTER, GIT_COMMITTER_EMAIL), Actor(GIT_AUTHOR, GIT_AUTHOR_EMAIL))
            log.info("Started creating stubs.")
            creator.create_stubs(templates.STUB_COMMIT_MSG, templates.STUB_FILE_CONTENT)
            log.info("Finished updating stub TBC files.")

        # UPDATING Issues / Projects
        try:
            updater = GithubUpdater(tracks, github_repo)
            if top_issues:
                log.info("Started updating issues on Github.")

                open_issues = updater.update_issues(bot_label=bot_label,
                                                    title_template=templates.ISSUE_TITLE,
                                                    tbc_template=templates.ISSUE_BODY_TBC,
                                                    tbi_template=templates.ISSUE_BODY_TBI,
                                                    update_template=templates.ISSUE_BODY_UPDATE,
                                                    utd_template=templates.ISSUE_BODY_UTD)
                log.info("Finished updating issues on Github.")
            if top_projects:
                log.info("Started updating Projects on Github.")

                updater.update_projects(title_template=templates.PROJECT_TITLE,
                                        body_template=templates.PROJECT_DESCRIPTION,
                                        tbc_column_template=templates.PROJECT_COLUMN_TBC,
                                        tbi_column_template=templates.PROJECT_COLUMN_TBI,
                                        update_column_template=templates.PROJECT_COLUMN_UPDATE,
                                        utd_column_template=templates.PROJECT_COLUMN_UTD,
                                        tbc_card_template=templates.PROJECT_CARD_TBC,
                                        tbi_card_template=templates.PROJECT_CARD_TBI,
                                        update_card_template=templates.PROJECT_CARD_UPDATE,
                                        utd_card_template=templates.PROJECT_CARD_UTD)

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
        print("::set-output name=translation-status::{}".format(out_status))
        if top_issues:
            out_issues = ','.join([str(number) for number in open_issues])
            print("::set-output name=open-issues::{}".format(out_issues))
        else:
            print("::set-output name=open-issues::")

    except Exception as e:
        log.critical("Got an unexpected error, exiting.")
        log.debug("Unexpected exception: {}".format(traceback.format_exc()))
        exit(1)
