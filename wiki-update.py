import requests
#from urllib.parse import quote
from enum import Enum, unique
import logging as log
from os import environ
import json
import sys
from git import Repo


GITHUB_API_URL = "https://api.github.com"
GITHUB_URL = "https://github.com"
GITHUB_RAW_URL = "https://raw.githubusercontent.com"
#ISSUE_TITLE_FORMAT = "Translation update required on {}"
#ISSUE_TBC_LABEL = "translation:init"
#ISSUE_UPDATE_LABEL = "translation:update"
#ISSUE_UTD_LABEL = "translation:ok"

#FILE_SUFFIX = ".md"

# OFFICIAL Github repo and branch variables
#OF_AUTHOR = "beat-saber-modding-group"
#OF_REPO = "wiki"
#OF_BRANCH = "master"

# TRANSLATION Github repo and branch variables
#TR_AUTHOR = "Awagi"
#TR_REPO = "wiki"
#TR_BRANCH = "frtranslation"

# ORIGINAL files variables
#OR_FILES_PATH = "wiki"
#OR_FILES_BLACKLIST = ["wiki/.vuepress", "wiki/fr"]

# TRANSLATED files variables
#TR_FILES_PATH = "wiki/fr"
#TR_FILES_BLACKLIST = []

# Github Issues variables
#ISSUE_BOT_LABEL = "WUT"




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

#def fetch_status_api(of_author, of_repo, of_branch, tr_author, tr_repo, tr_branch, or_files_path, tr_files_path, or_files_blacklist=[], tr_files_blacklist=[], file_suffixes=[".md"]):
#    """
#    Fetch information from Github using Github API to track changes within original files, used as basis for translated files.
#
#    While we differenciate two Github repositories/branches, they must have the particular
#    same structure to store the original files.
#    There are:
#        - the official repository, where original files are considered up-to-date.
#        - the translation repository, where translated files are being built.
#
#    About the different files, each representing 1 Wiki page:
#        - the original files, which are used as basis for translated files.
#        - the translated files, which are simply translations of original files, nothing more.
#
#    Original files and translated files must follow the same file structure and terminology within
#    their own folder described as ``or_files_path`` and ``tr_files_path``
#
#    The function do the following:
#        1. Fetch original wiki files and check for matching translated files.
#        2. Check if any translated file requires changes.
#        2.1. Get the commit where the translated file was lastly updated.
#        2.2. Compare the original file from that commit to the lately commited original file.
#
#    :param of_author: the official repository author
#    :param of_repo: the official repository with the up-to-date original files
#    :param of_branch: the branch on the official repository with the up-to-date original files
#    :param tr_author: the translation repository author
#    :param tr_repo: the translation repository with the work in progress translated files
#    :param tr_branch: the branch on the translation repository with the work in progress translated files
#    :param or_files_path: the path of the original files, must be the same on both the translation repository and the official repository
#    :param tr_files_path: the path of the translated files within the translation repository
#    :param or_files_blacklist: a list of untracked original files represented as stringed paths
#    :param tr_files_blacklist: a list of untracked translated files represented as stringed paths
#    :param file_suffixes: the suffixes file for tracked files (generally wiki pages from vuepress are .md files)
#
#    :return: a list of translated file, with their Status and links to compare base original files and head original files
#    
#    :example:
#    [
#        {
#            "translation": {
#                "path": "wiki/fr/README.md",
#                "url": "https://github.com/Awagi/wiki/blob/frtranslation/wiki/fr/README.md",
#                "commit": "1b7275d387b3ac6cf2e2cf9389e576ca1e470107",
#                "status": "UPDATE"
#            },
#            "original": {
#                "path": "wiki/README.md",
#                "sha": "1e71ef0a8f23b514c2621a4305eaa0904f33741b",
#                "compare_url": "https://github.com/beat-saber-modding-group/wiki/compare/1b7275d387b3ac6cf2e2cf9389e576ca1e470107...beat-saber-modding-group:master",
#                "url": "https://github.com/beat-saber-modding-group/wiki/blob/68a959f23e324ae85dea5742b2e11093cdc14e2a/wiki/README.md",
#                "old_url": "https://github.com/beat-saber-modding-group/wiki/blob/1b7275d387b3ac6cf2e2cf9389e576ca1e470107/wiki/README.md",
#                "raw_url": "https://github.com/beat-saber-modding-group/wiki/raw/68a959f23e324ae85dea5742b2e11093cdc14e2a/wiki/README.md",
#                "old_raw_url": "https://raw.githubusercontent.com/beat-saber-modding-group/wiki/1b7275d387b3ac6cf2e2cf9389e576ca1e470107/wiki/README.md",
#                "patch": "@@ -37,7 +37,7 @@ footer: Copyright \u00a9 2019 Beat Saber Modding Group | Licensed under CC BY-NC-SA\n * [BeatMods](https://beatmods.com) - Repository of mods that are reflected in installers like ModAssistant\n * [BeatSaver](https://beatsaver.com/) - Download custom songs here\n * [BeastSaber](https://bsaber.com/) - Reviews, articles, playlists, and more!\n-* [ModelSaber](https://modelsaber.com/) - Download custom sabers, avatars, and platforms!\n+* [ModelSaber](https://modelsaber.com/) - Download custom sabers, avatars, blocks, and platforms!\n * [ScoreSaber](https://scoresaber.com/) - Custom leaderboards\n * [Steam Store Page](https://store.steampowered.com/app/620980/Beat_Saber/)\n * [Oculus Store Page](https://www.oculus.com/experiences/rift/1304877726278670/)",
#                "additions": 1,
#                "deletions": 1,
#                "changes": 2
#            }
#        }
#    ]
#    """
#    # Fetch most recent original wiki files from the official up-to-date repo and branch
#    log.info("Fetching head original wiki files from Github")
#    dir_url = "{}/repos/{}/{}/contents/{}?ref={}".format(GITHUB_API_URL, of_author, of_repo, or_files_path, of_branch)
#    head_or_files = fetch_files_api(dir_url, file_suffixes, or_files_blacklist)
#
#    nb_files = len(head_or_files)
#    log.debug("{} head original files found in the official repo".format(nb_files))
#
#    cnt_tbc = 0
#    cnt_update = 0
#    cnt_utd = 0
#    cnt_tbi = 0
#
#    # Fetch every translated files based on the original files
#    files = []
#    cnt = 0
#    for or_file in head_or_files:
#        cnt = cnt + 1
#        or_path = or_file["path"]
#        tr_path = or_to_tr_path(or_path)
#        f = {
#            "translation": {
#                "path": tr_path,
#                "url": "{}/{}/{}/blob/{}/{}".format(GITHUB_URL, tr_author, tr_repo, tr_branch, tr_path)
#            },
#            "original": {
#                "path": or_path,
#                "sha": or_file["sha"]
#            }
#        }
#
#        log.info("[{}/{}] Comparing base original file to head original file from {}".format(cnt, nb_files, tr_path))
#
#        log.debug("Get last commit updating translated file {}".format(tr_path))
#        res = call_api(Method.GET, "{}/repos/{}/{}/commits?sha={}&path={}".format(GITHUB_API_URL, tr_author, tr_repo, tr_branch, quote(tr_path, safe='')))
#        if len(res) == 0:
#            # no commit means the file doesn't exist
#            f["translation"]["status"] = Status.TBC
#            cnt_tbc = cnt_tbc + 1
#        else:
#            tr_commit = res[0]["sha"]
#            f["translation"]["commit"] = tr_commit
#            f["original"]["compare_url"] = "{}/{}/{}/compare/{}...{}:{}".format(GITHUB_URL, of_author, of_repo, tr_commit, of_author, of_branch)
#
#            # compare from translation commit to today's up-to-date head files
#            log.debug("Compare original file {} to head file".format(or_path))
#            res = call_api(Method.GET, "{}/repos/{}/{}/compare/{}...{}:{}".format(GITHUB_API_URL, of_author, of_repo, tr_commit, of_author, of_branch))
#
#            # find the original file in the comparison
#            or_comp = next((x for x in res["files"] if x["filename"] == or_path), None)
#
#            if or_comp is None:
#                # original file not found in comparison: means it hasn't been updated
#                f["translation"]["status"] = Status.UTD
#                cnt_utd = cnt_utd + 1
#            elif or_comp["status"] == "added":
#                # original file recently added, the translated file must be either initialized (although already created)
#                f["translation"]["status"] = Status.TBI
#                cnt_tbi = cnt_tbi + 1
#                f["original"]["url"] = or_comp["blob_url"]
#                f["original"]["raw_url"] = or_comp["raw_url"]
#            elif or_comp["status"] == "modified":
#                # original file found with modifications
#                f["translation"]["status"] = Status.Update
#                cnt_update = cnt_update + 1
#                f["original"]["url"] = or_comp["blob_url"]
#                f["original"]["old_url"] = "{}/{}/{}/blob/{}/{}".format(GITHUB_URL, OF_AUTHOR, OF_REPO, f["translation"]["commit"], f["original"]["path"])
#                f["original"]["raw_url"] = or_comp["raw_url"]
#                f["original"]["old_raw_url"] = "{}/{}/{}/{}/{}".format(GITHUB_RAW_URL, OF_AUTHOR, OF_REPO, f["translation"]["commit"], f["original"]["path"])
#                f["original"]["patch"] = or_comp["patch"]
#                f["original"]["additions"] = or_comp["additions"]
#                f["original"]["deletions"] = or_comp["deletions"]
#                f["original"]["changes"] = or_comp["changes"]
#
#            files.append(f)
#
#    log.info("{} files to create and initialize".format(cnt_tbc))
#    log.info("{} files to initialize".format(cnt_tbi))
#    log.info("{} files to update".format(cnt_update))
#    log.info("{} files up-to-date".format(cnt_utd))
#
#    return files


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
                                if oldori.binsha == ori.binsha:
                                    # base original and latest original page are the same, translation page is up-to-date
                                    log.debug("{} is UP-TO-DATE".format(trapath))
                                    status = Status.UTD
                            except:
                                # corresponding original page didn't exist at translation page creation, then the latter was just created but has to be initialized now
                                log.debug("{} has TO BE INITIALIZED".format(trapath))
                                status = Status.TBI

                            if status is None:
                                # there we know base original and latest original pages have a difference
                                log.debug("{} has to be UPDATED, getting diff".format(trapath))
                                status = Status.Update

                                # get diff to get applied patch
                                diff = oldcommit.diff(paths=ori.path, create_patch=True)[0]
                                patch = diff.diff
                                # get additions, deletions and changes
                                insertions = 0
                                deletions = 0
                                lines = 0
                                for c in repo.iter_commits(oldcommit, paths=ori.path):
                                    stats = c.stats.files[ori.path]
                                    insertions = insertions + stats["insertions"]
                                    deletions = deletions + stats["deletions"]
                                    lines = lines + stats["lines"]

                        o = {
                            "translation": {
                                "path": trapath,
                                "status": status
                            },
                            "original": {
                                "path": ori.path,
                                "lastsha": ori.hexsha,
                                "lastcommit": repo.active_branch.commit.hexsha
                            }
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
        compare_url = "{}/{}/compare/{}...{}#files_bucket".format(GITHUB_URL, repo, status["translation"]["commit"], status["original"]["lastcommit"])
        oldori_raw_url = "{}/{}/raw/{}/{}".format(GITHUB_URL, repo, status["translation"]["commit"], status["original"]["path"])
        ori_raw_url = "{}/{}/raw/{}/{}".format(GITHUB_URL, repo, status["original"]["lastcommit"], status["original"]["path"])
        # build body
        if status["translation"]["status"] is Status.Update:
            
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
                'Thanks to your involvement, {o[translation][path]} is up-to-date! :1st_place_medal:\n'
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
    #tr_files = fetch_status_api(of_author=OF_AUTHOR,
    #                            of_repo=OF_REPO,
    #                            of_branch=OF_BRANCH,
    #                            tr_author=TR_AUTHOR,
    #                            tr_repo=TR_REPO,
    #                            tr_branch=TR_BRANCH,
    #                            or_files_path=OR_FILES_PATH,
    #                            tr_files_path=TR_FILES_PATH,
    #                            or_files_blacklist=OR_FILES_BLACKLIST,
    #                            tr_files_blacklist=TR_FILES_BLACKLIST,
    #                            file_suffixes=[FILE_SUFFIX])
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

