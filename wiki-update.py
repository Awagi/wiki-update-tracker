import requests
from enum import Enum, unique
import logging as log
from os import environ
import json
import sys
from git import Repo
import re
import frontmatter
from yaml.scanner import ScannerError


GITHUB_API_URL = "https://api.github.com"
GITHUB_URL = "https://github.com"
GITHUB_RAW_URL = "https://raw.githubusercontent.com"

# Frontmatter Metadata key and value that, found in translation pages headers, tells WUT the page has not been initialized
HEADER_TBI_KEY = "translation-done"
HEADER_TBI_VALUE = False


@unique
class Method(str, Enum):
    POST = "POST"
    GET = "GET"
    PATCH = "PATCH"


@unique
class Status(str, Enum):
    TBC = "TBC"  # To Be Created, this kind of file must be initialized with a first translation
    TBI = "TBI"  # To Be Initialized, the translated file exists but was not initialized with a starting translation
    UTD = "UTD"  # Up To Date, nothing to be done here, the translation file was based on the latest original english file
    Update = "UPDATE"  # requires an update


class APIResponseException(Exception):
    pass


class APINotFoundException(APIResponseException):
    pass


def call_api(method, path, token, json={}, headers={}):
    """
    Call Github API and return the JSON body.
    Next pages are automatically called when needed to return the full body response.
    Rate Limit can apply (https://developer.github.com/v3/rate_limit/).
    Authorization token is mandatory here.
    """
    uri = "{}{}".format(GITHUB_API_URL, path)
    headers["Authorization"] = "Bearer {}".format(token)

    ret = None

    while uri:
        if method == Method.POST:
            req = requests.post(uri, json=json, headers=headers)
        elif method == Method.PATCH:
            req = requests.patch(uri, json=json, headers=headers)
        elif method == Method.GET:
            req = requests.get(uri, headers=headers)
        else:
            return None

        log.debug("Got status {} from {} {}".format(req.status_code, method, req.url))
        if req.status_code == 404:
            raise APINotFoundException("Got 404 Not Found from Github API")
        elif req.status_code >= 300:
            raise APIResponseException("Response {} from Github API".format(req.json()))

        body = req.json()
        if ret is None:
            ret = body
        else:
            # means we're in the second round in loop, i.e the URL has a "next" Link header, i.e the response is an array
            ret.extend(body)
        if req.links.get("next"):
            uri = req.links["next"]["url"]
        else:
            uri = None

    return ret


def fetch_status_local(git_repo, original_path, translation_paths, original_blacklist=[], file_suffixes=[".md"]):
    """
    Fetch diffs between original wiki pages from the git repo to track changes and report about the action to be taken on translation files.

    This function returns the same as fetch_status_api, but has way better efficiency in this task.
    On the other hand, it requires the git repo to exist on the system and be accessible through the path given in git_repo.

    The reference branch is the active one in the repo. Checkout if you need to change branch.

    :param git_repo: the git repo path on the system
    :param original_path: the relative path within repo where original wiki pages are stored
    :param translation_paths: the relative paths within repo where translations are stored
    :param original_blacklist: list of ignored original files, using relative paths within the repo, may be files or entire folders to ignore
    :param file_suffixes: allowed suffixes to check

    :return: a list of translated file, with their Status and comparative information

    :example:
    [
        {
            "translation": {
                "path": "wiki/fr/README.md",
                "status": "UPDATE",
                "sha": "4968dacd134fc6861ebe009bdc52c7a211055a84",
                "commit": "1b7275d387b3ac6cf2e2cf9389e576ca1e470107"
            },
            "original": {
                "path": "wiki/README.md",
                "lastsha": "1e71ef0a8f23b514c2621a4305eaa0904f33741b",
                "lastcommit": "65ad3ad66e9513bbab7d09ed666c5198271e1508",
                "oldsha": "4c08158aa90ffeb3d10dcb2f06728acdcd92b31e",
                "patch": "@@ -37,7 +37,7 @@ footer: Copyright \xc2\xa9 2019 Beat Saber Modding Group | Licensed under CC BY-NC-SA\n * [BeatMods](https://beatmods.com) - Repository of mods that are reflected in installers like ModAssistant\n * [BeatSaver](https://beatsaver.com/) - Download custom songs here\n * [BeastSaber](https://bsaber.com/) - Reviews, articles, playlists, and more!\n-* [ModelSaber](https://modelsaber.com/) - Download custom sabers, avatars, and platforms!\n+* [ModelSaber](https://modelsaber.com/) - Download custom sabers, avatars, blocks, and platforms!\n * [ScoreSaber](https://scoresaber.com/) - Custom leaderboards\n * [Steam Store Page](https://store.steampowered.com/app/620980/Beat_Saber/)\n * [Oculus Store Page](https://www.oculus.com/experiences/rift/1304877726278670/)\n",
                "additions": 1,
                "deletions": 1,
                "changes": 2
            }
        }
    ]
    """
    # TODO pre conditions on params

    repo = Repo(git_repo)

    log.info("Fetching head original wiki files from local repo.")

    ignored = original_blacklist + translation_paths
    ret = []

    # fetch original and translation files
    tree = repo.active_branch.commit.tree
    oritree = tree[original_path]
    for t in [oritree] + oritree.trees:
        if t.path not in ignored:
            for ori in t.blobs:
                if ori.path not in ignored:
                    for translation_path in translation_paths:
                        # find translation page
                        trapath = "{}{}".format(translation_path, ori.path[len(original_path):])
                        log.debug("Checking {}".format(trapath))
                        status = None
                        try:
                            tra = tree[trapath]
                        except KeyError:
                            # corresponding translation page doesn't exist, it must be created
                            log.debug("{} has TO BE CREATED and initialized".format(trapath))
                            status = Status.TBC

                        if status is None:
                            # get last commit from translation file
                            it = repo.iter_commits(paths=trapath, max_count=1)
                            oldcommit = list(it)[0]
                            try:
                                # get base (old) original file from this commit
                                oldori = oldcommit.tree[ori.path]
                                # checking translation page's header: if it tells us it is not initialized yet, don't go further in checking original page changes
                                post = frontmatter.loads(tra.data_stream.read())
                                if HEADER_TBI_KEY in post and post[HEADER_TBI_KEY] == HEADER_TBI_VALUE:
                                    log.debug("{} has TO BE INITIALIZED (found user defined header)".format(trapath))
                                    status = Status.TBI
                            except KeyError:
                                # corresponding original page didn't exist at translation page creation, then the latter was just created but has to be initialized now
                                log.debug("{} has TO BE INITIALIZED".format(trapath))
                                status = Status.TBI
                            except ScannerError:
                                pass

                            if status is None:
                                if oldori.binsha == ori.binsha:
                                    # base original and latest original page are the same, translation page is up-to-date
                                    log.debug("{} is UP-TO-DATE".format(trapath))
                                    status = Status.UTD
                                else:
                                    # there we know base original and latest original pages have a difference
                                    log.debug("{} has to be UPDATED, getting diff".format(trapath))
                                    status = Status.Update

                                    # get diff to get applied patch
                                    diff = oldcommit.diff(paths=ori.path, create_patch=True)[0]
                                    patch = diff.diff
                                    # get additions, deletions and changes
                                    insertions = diff.diff.count(b"\n+")
                                    deletions = diff.diff.count(b"\n-")
                                    lines = insertions + deletions

                        o = {
                            "translation": {
                                "path": trapath,
                                "status": status
                            },
                            "original": {
                                "path": ori.path,
                                "lastsha": ori.hexsha,
                                "lastcommit": repo.active_branch.commit.hexsha
                            },
                            "context": {
                                "branch": repo.active_branch.name
                            }
                        }
                        if status is Status.TBI or status is Status.UTD or status is Status.Update:
                            o["translation"]["sha"] = tra.hexsha
                            o["translation"]["commit"] = oldcommit.hexsha
                        if status is Status.UTD or status is Status.Update:
                            o["original"]["oldsha"] = oldori.hexsha
                        if status is Status.Update:
                            # build object from UPDATE basis
                            o["original"]["patch"] = patch.decode('utf-8')
                            o["original"]["additions"] = insertions
                            o["original"]["deletions"] = deletions
                            o["original"]["changes"] = lines
                        if status is None:
                            log.warning("Hu ho, we shouldn't have come to this place (from {})".format(trapath))
                        ret.append(o)

    return ret


def update_issues(token, files_status, repo, bot_label):
    """
    Update issues on Github according to the given files status.

    The idea is to have an issue per translation page to track:
        - open issues for translated pages to update, to create and to initialize
        - closed issues for up-to-date translated pages

    :param token: the Github App token, with read/write access to issues
    :param files_status: a list of files with their translation status (format must match fetch_status_local return)
    :param repo: the remote repository on which to update issues, such as 'Author/Repo'
    :param bot_label: the bot Github label placed on issues to update when the script creates these
    """
    # List issues from repository having the bot label
    log.debug("Fetch existing issues from Github")
    # WARNING on this one: The API may change without advance notice during the preview period (https://developer.github.com/v3/issues/#list-repository-issues)
    issues = call_api(Method.GET, "/repos/{}/issues?labels={}&state=all&per_page=100".format(repo, bot_label), token)

    ret = []  # store updated and created open issue numbers
    total = len(files_status)
    cnt = 0
    for status in files_status:
        cnt = cnt + 1
        tr_path = status["translation"]["path"]
        log.info("[{}/{}] Updating issue for {}".format(cnt, total, tr_path))

        # forge Github URLs, be aware they can't be used in every contexts
        tr_url = "{}/{}/blob/{}/{}".format(GITHUB_URL, repo, status["context"]["branch"], tr_path)
        or_url = "{}/{}/blob/{}/{}".format(GITHUB_URL, repo, status["original"]["lastcommit"], status["original"]["path"])
        # build body
        if status["translation"]["status"] is Status.Update:
            compare_url = "{}/{}/compare/{}...{}#files_bucket".format(GITHUB_URL, repo, status["translation"]["commit"], status["original"]["lastcommit"])
            oldori_raw_url = "{}/{}/raw/{}/{}".format(GITHUB_URL, repo, status["translation"]["commit"], status["original"]["path"])
            ori_raw_url = "{}/{}/raw/{}/{}".format(GITHUB_URL, repo, status["original"]["lastcommit"], status["original"]["path"])
            body = (
                '## :bookmark_tabs: Translation update\n'
                'Since **`{o[translation][path]}`** was last updated, changes have been detected in the original wiki page `{o[original][path]}` it is based on.\n'
                '\n'
                'Please update **[the translation here]({tr_url})** accordingly, respecting contribution guidelines.\n'
                '\n'
                '### :bar_chart: Workload\n'
                '\n'
                'Calculated changes made to the original file `{o[original][path]}` (as lines):\n'
                '\n'
                '```diff\n'
                '+ {o[original][additions]} additions\n'
                '- {o[original][deletions]} deletions\n'
                '! {o[original][changes]} total lines updated\n'
                '```\n'
                '\n'
                '### :wrench: Translation tools\n'
                '\n'
                'You can choose one of the following options to help you see what changed:\n'
                '1. Use this [Github comparison]({compare_url}) and find the comparison on the file **`{o[original][path]}`**.\n'
                '2. OR use [Diffchecker web version](https://www.diffchecker.com/). Copy/paste [this original text]({oldori_raw_url}) in the left field and [this changed text]({ori_raw_url}) in the right field, then press "Find Difference".\n'
                '3. OR simply use the detailed patch below.\n'
                '\n'
                'Detailed additions and deletions on `{o[original][path]}`:\n'
                '```diff\n'
                '{o[original][patch]}\n'
                '```\n'
            ).format(o=status, tr_url=tr_url, compare_url=compare_url, oldori_raw_url=oldori_raw_url, ori_raw_url=ori_raw_url)
            label = "translation:update"
            state = "open"
        elif status["translation"]["status"] is Status.TBC:
            body = (
                '## :page_facing_up: Translation creation & initialization\n'
                'A new original wiki page has been detected: `{o[original][path]}`. It has no associated translation yet.\n'
                '\n'
                'Please create the file **{o[translation][path]}** and initialize the translation based on the [original English version]({or_url}).\n'
            ).format(o=status, or_url=or_url)
            label = "translation:new"
            state = "open"
        elif status["translation"]["status"] is Status.TBI:
            body = (
                '## :page_facing_up: Translation initialization\n'
                'A new original wiki page has been detected: `{o[original][path]}`. It has no associated translation yet (though the file `{o[translation][path]}` already exists).\n'
                '\n'
                'Please **[initialize the translation here]({tr_url})**. Base your translation on the [original English version]({or_url}).\n'
            ).format(o=status, tr_url=tr_url, or_url=or_url)
            label = "translation:new"
            state = "open"
        elif status["translation"]["status"] is Status.UTD:
            body = (
                '## :heavy_check_mark: Nothing to do\n'
                'Thanks to your involvement, `{o[translation][path]}` is up-to-date! :1st_place_medal:\n'
                '\n'
                'Let\'s keep it that way for every wiki pages!\n'
            ).format(o=status)
            label = "translation:ok"
            state = "closed"
        else:
            log.warning("Unexpected behaviour detected.")
            body = ':bug: This is an unexpected issue description, I\'m probably broken. Please report this bug to some maintainer.\n'
            label = "bug"
            state = "closed"

        title = "Translation page: {}".format(tr_path)
        issue_finder = (issue for issue in issues if issue["title"] == title)
        issue = next(issue_finder, None)

        if issue is None:
            log.debug("File {} doesn't have an existing issue, creating it".format(tr_path))
            issue = call_api(Method.POST, "/repos/{}/issues".format(repo), token, json={
                "title": title,
                "body": body,
                "labels": [bot_label, label]
            })
            log.debug("Succesfully created issue {}".format(issue["number"]))
            # closing the created issue afterward if state to 'closed'
            if state == "closed":
                call_api(Method.PATCH, "/repos/{}/issues/{}".format(repo, issue["number"]), token, json={
                    "state": state
                })
                log.debug("Successfully closed issue {}".format(issue["number"]))
        else:
            for duplicate in issue_finder:
                log.debug("Found duplicate issue {}, marking and closing it".format(duplicate["number"]))
                call_api(Method.PATCH, "/repos/{}/issues/{}".format(repo, duplicate["number"]), token, json={
                    "labels": ["duplicate"],
                    "state": "closed"
                })
            log.debug("Found issue for file {}, updating it".format(status["translation"]["path"]))
            res = call_api(Method.PATCH, "/repos/{}/issues/{}".format(repo, issue["number"]), token, json={
                "title": title,
                "body": body,
                "labels": [bot_label, label],
                "state": state
            })
            log.debug("Successfully updated issue {}".format(res["number"]))

        if state == "open":
            ret.append(issue["number"])

    return ret


if __name__ == '__main__':
    logformat = "[%(asctime)s][%(levelname)s] %(message)s"
    log.basicConfig(level=log.INFO, format=logformat)

    # Launch the script with below args, and from the git repo directory
    # expected args:
    # 0: script name
    # 1: repo local path
    # 2: original pages relative path
    # 3: ignored files relative paths
    # 4: translation pages relative paths
    # 5: file suffix
    # 6: Github repo ('author/repo')
    # 7: bot label
    # 8: token
    # 9: log level ('DEBUG', 'INFO', 'WARNING' or 'CRITICAL')
    if len(sys.argv) < 10:
        log.critical("Can't operate without params.")
        exit(1)

    log.getLogger().setLevel(sys.argv[9])

    repo_path = sys.argv[1]
    original_path = sys.argv[2]
    ignored_paths = sys.argv[3]
    translation_paths = sys.argv[4]
    file_suffix = sys.argv[5]
    repo = sys.argv[6]
    bot_label = sys.argv[7]
    token = sys.argv[8]

    if len(ignored_paths) == 0:
        ignored_paths = []
    else:
        ignored_paths = ignored_paths.split(',')
    if len(translation_paths) == 0:
        translations_paths = []
    else:
        translation_paths = translation_paths.split(',')

    log.info("Started fetching Wiki pages status.")
    tr_files = fetch_status_local(git_repo=repo_path,
                                  original_path=original_path,
                                  translation_paths=translation_paths,
                                  original_blacklist=ignored_paths,
                                  file_suffixes=[file_suffix])
    log.info("Finished fetching Wiki pages status.")

    try:
        log.info("Started updating issues on Github.")

        open_issues = update_issues(token=token,
                                    files_status=tr_files,
                                    repo=repo,
                                    bot_label=bot_label)
        log.info("Finished updating issues on Github.")
    except APIResponseException as e:
        log.critical("Got an unexpected API response, exiting.")
        log.debug("Unexpected response: {}".format(str(e)))
        exit(1)

    out_status = ','.join(["{}:{}".format(f["translation"]["path"], f["translation"]["status"]) for f in tr_files])
    out_issues = ','.join([str(number) for number in open_issues])
    print("::set-output name=translation-status::{}".format(out_status))
    print("::set-output name=open-issues::{}".format(out_issues))

