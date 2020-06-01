from enum import Enum, unique
from constants import RFC5646_LANGUAGE_TAGS
from git import Repo, Actor, InvalidGitRepositoryError, NoSuchPathError
# logs for debugging
import logging as log
# to read header in markdown through frontmatter
import frontmatter
from yaml.scanner import ScannerError
from constants import HEADER_TBI_KEY, HEADER_TBI_VALUE
from pathlib import Path
import glob


class TrackerException(Exception):
    """
    Raised when an exception during tracking stage occurs.
    """
    pass


class SamePathException(TrackerException):
    """
    Raised when both original and translation paths are the same.
    """
    pass


class LanguageTagException(TrackerException):
    """
    Raised when a given language tag doesn't exist as of RFC 5646.
    """
    pass


class TranslationTrackInfo:
    """
    Translation info after fetching their status based on git:
        - `translation`: a TranslationFileInfo object, the translation file
        - `original`: a FileInfo object, the latest (according to current commit) original file
        - `base_original`: a FileInfo object, the original file the translation was based on (same as original if status is UTD, None if status is TBI or TBC)
        - `status`: the status for the translation file (`Status` enum)
        - `patch`: a PatchInfo object representing the diff between `original` and `base_original`, if status is `Status.Update`, otherwise None
        - `branch`: name of the git branch where tracking was done
    """
    def __init__(self, translation, original, base_original, status, patch, branch):
        if isinstance(translation, TranslationFileInfo):
            self.translation = translation
        else:
            raise ValueError("translation must be an instance of TranslationFileInfo")
        if isinstance(original, FileInfo):
            self.original = original
        else:
            raise ValueError("original must be an instance of FileInfo")
        if isinstance(base_original, FileInfo):
            self.base_original = base_original
        else:
            raise ValueError("base_original must be an instance of FileInfo")
        if isinstance(status, Status):
            self.status = status
        else:
            raise ValueError("status must be an instance of Status")
        if isinstance(patch, PatchInfo):
            self.patch = patch
        else:
            raise ValueError("patch must be an instance of PatchInfo")
        self.branch = branch


@unique
class Status(str, Enum):
    TBC = "To Create"  # this kind of file must be initialized with a first translation
    TBI = "To Initialize"  # the translated file exists but was not initialized with a starting translation
    UTD = "Up-To-Date"  # nothing to be done here, the translation file was based on the latest original english file
    Update = "To Update"  # requires an update
    Orphan = "Orphan"  # translation file has no corresponding original file



class FileInfo:
    """
    Contains info about a file to track:
        - `path`: its relative path within the git repo
        - `blob`: file blob representation (Blob object from git)
        - `commit`: blob from this commit (Commit object from git)
    """
    def __init__(self, path, blob=None, commit=None):
        self.path = path
        self.blob = blob
        self.commit = commit


class TranslationFileInfo(FileInfo):
    """
    Same as FileInfo with the language tag from RFC 5646:
        - `lang_tag`: language tag / code like 'fr' or 'fr-FR'
        - `language`: equivalent language
    """
    def __init__(self, path, lang_tag, blob=None, commit=None):
        super().__init__(path, blob, commit)
        self.lang_tag = lang_tag

    def __setattr__(self, name, value):
        if name == 'lang_tag':
            try:
                super().__setattr__('language', RFC5646_LANGUAGE_TAGS[value])
            except KeyError:
                raise LanguageTagException()
            super().__setattr__('lang_tag', value)
        elif name == 'language':
            raise NotImplementedError("can't change language, use lang_tag")
        else:
            super().__setattr__(name, value)


class PatchInfo:
    """
    Contains info about a tracked file that requires an update:
        - `diff`: str representing a git diff
        - `additions`: number of added lines
        - `deletions`: number of deleted lines
        - `changes`: total number of changes (additions + deletions)
    """
    def __init__(self, diff="", additions=0, deletions=0, changes=0):
        self.diff = diff
        self.additions = additions
        self.deletions = deletions
        self.changes = changes


def fetch_files(path, glob_filter, glob_ignore):
    """
    Fetch files within a path matching glob_filter patterns and not glob_ignore patterns.

    :param path: pathlib.Path, a valid directory path
    :param glob_filter: list of str, glob-like patterns for files to filter relative to path
    :param glob_ignore: list of str, glob-like patterns for files to ignore relative to path
    :return: the list of resulting pathlib.Path
    """
    files = []
    excludes = []
    for gi in glob_ignore:
        ex = glob.iglob("{}/{}".format(path.as_posix(), gi), recursive=True)
        excludes.extend([Path(n) for n in ex])
    for gf in glob_filter:
        fi = glob.iglob("{}/{}".format(path.as_posix(), gf), recursive=True)
        for n in fi:
            p = Path(n)
            if p.is_file() and p not in excludes:
                files.append(p)
    return files


class TranslationTracker:
    """
    Represents the tracking part of the script, checking existent/non existent translation files and diff when changes where applied to original file.
    """
    def __init__(self, git_repo):
        """
        Creates the tracker for the specified language (use the tag from RFC 5646) and link the preliminary setup git repo.

        :param git_repo: the git Repo object
        """
        self.map = {}  # key: translation filepath, original FileInfo
        self.originals = {}  # keep track of generated original files FileInfo (key: str path, value: original file FileInfo)
        self.repo = git_repo

    def put(self, translation_path, original_path, lang_tag, glob_ignore=[], glob_filter=["**/*"]):
        """
        Puts a translation file or directory in the tracker, and maps/remaps it to its reflected based original file or directory.

        Be a directory, every files within `original_path` will be added according to filter.
        Also, as directories, `original_path` and `translation_path` must have the same structure and filenames.

        Be a file, `original_path` must exist.

        :param translation_path: pathlib.Path, a valid path relative to the git repo, different from `original_path`
        :param original_path: pathlib.Path, a valid path relative to the git repo
        :param lang_tag: str, the language tag from RFC 5646 to apply on this translation
        :param glob_filter: list of str, glob patterns to filter files to be tracked, defaults to all files
        :param glob_ignore: list of str, glob patterns to filter files to be ignored if matching a filter
        :raise SamePathException: when original and translation paths are the same
        :raise ValueError: when original file is not found in repo
        :raise LanguageTagException: when given language tag is not referenced in RFC 5646
        """
        if translation_path == original_path:
            raise SamePathException()

        if original_path.is_file():
            
        # get every existing original files and translation files
        originals = fetch_files(original_path, glob_filter, glob_ignore)
        translations = fetch_files(translation_path, glob_filter, glob_ignore)

        for original in originals:


        active_commit = self.repo.active_branch.commit
        tree = active_commit.tree
        try:
            original = tree[original_path]
        except KeyError:
            raise ValueError("original file not found")
        if original.type == 'tree':
            treebuffer = [original]
            ignored = ignore + [translation_path]
            while len(treebuffer) > 0:
                t = treebuffer.pop()
                if t.path not in ignored:
                    treebuffer.extend(t.trees)
                    for original_file in t.blobs:
                        # last check for translation file: not ignored and has suffixes if suffix are set
                        if original_file.path not in ignored and (len(suffixes) == 0 or len(suffixes) > 0 and len([i for i in suffixes if original_file.path.endswith(i)]) > 0):
                            # forge translation file path
                            translation_file_path = "{}{}".format(translation_path, original_file.path[len(original_path):])
                            log.debug("Mapped translation file '{}' to original file '{}', latest commit '{}'".format(translation_file_path, original_file.path, active_commit.hexsha))
                            translation_info = TranslationFileInfo(translation_file_path, lang_tag)
                            if original_file.path in self.originals:
                                original_info = self.originals[original_file.path]
                            else:
                                original_info = FileInfo(original_file.path, blob=original_file, commit=active_commit)
                                self.originals[original_file.path] = original_info
                            self.map[translation_info] = original_info

        elif original.type == 'blob':
            log.debug("{} will be tracked".format(translation_path))
            translation_info = TranslationFileInfo(translation_path, lang_tag)
            if original_path in self.originals:
                original_info = self.originals[original_path]
            else:
                original_info = FileInfo(original_path, blob=original, commit=active_commit)
                self.originals[original_path] = original_info
            self.map[translation_info] = original_info

    def track(self):
        """
        Tracks given files (`put` method) within the repo on active branch, returning their info.

        Basically, each translation file was modified in a commit.
        Based on this commit, we take the original file and compare it to the same original file on the current commit to know whether it was modified or not.
        Then we can tell the translation requires:
        - to be created (`Status.TBC`)
        - to be initialized (`Status.TBI`)
        - to be updated (`Status.Update`)
        - nothing, it's up-to-date (`Status.UTC`)

        This assumes the translation was correctly done based on the original file from this commit, as this function does not parse contents or anything.

        :return: a list of TranslationTrackInfo
        """
        tracks = []

        for translation in self.map.keys():
            original = self.map[translation]
            patch = PatchInfo()
            status = None

            # recent commit is from the existing original file, from which we will track down history in parent commits
            tree = original.commit.tree
            original_content = original.blob.data_stream.read()
            original_nb_lines = original_content.count(b'\n')

            # does translation file exist?
            try:
                translation.blob = tree[translation.path]
            except KeyError:
                # corresponding translation page doesn't exist for active_commit, it has to be created
                log.debug("{} has TO BE CREATED and initialized".format(translation.path))
                status = Status.TBC
                patch.diff = original_content
                patch.additions = original_nb_lines
                base_original = FileInfo(original.path)

            if status is None:
                # get last commit from translation file
                it = self.repo.iter_commits(rev=original.commit, paths=translation.path, max_count=1)
                translation.commit = list(it)[0]
                try:
                    # get base (old) original file from this commit
                    base_original = FileInfo(original.path, blob=translation.commit.tree[original.path], commit=translation.commit)
                    # if it can be loaded by frontmatter (markdown, ...), checking translation page's header: if it tells us it is not initialized yet, don't go further in checking original page changes
                    post = frontmatter.loads(translation.blob.data_stream.read())
                    if HEADER_TBI_KEY in post and post[HEADER_TBI_KEY] == HEADER_TBI_VALUE:
                        log.debug("{} has TO BE INITIALIZED (found user defined header)".format(translation.path))
                        status = Status.TBI
                        patch.diff = original_content
                        patch.additions = original_nb_lines
                except KeyError:
                    # corresponding original page didn't exist at translation page creation, then the latter was just created but has to be initialized now
                    log.debug("{} has TO BE INITIALIZED".format(translation.path))
                    status = Status.TBI
                    patch.diff = original_content
                    patch.additions = original_nb_lines
                except ScannerError:
                    pass

                if status is None:
                    if base_original.blob.binsha == original.blob.binsha:
                        # base original and latest original page are the same, translation page is up-to-date
                        log.debug("{} is UP-TO-DATE".format(translation.path))
                        status = Status.UTD
                    else:
                        # there we know base original and latest original pages have a difference
                        log.debug("{} has to be UPDATED, getting diff".format(translation.path))
                        status = Status.Update

                        # get diff to get applied patch
                        diff = base_original.commit.diff(original.commit, paths=base_original.path, create_patch=True)[0]
                        patch.diff = diff.diff.decode('utf-8')
                        # get additions, deletions and changes
                        patch.additions = diff.diff.count(b"\n+")
                        patch.deletions = diff.diff.count(b"\n-")
                        patch.changes = patch.additions + patch.deletions

            if status is None:
                log.warning("Hu ho, we shouldn't have come to this place (from {})".format(translation.path))

            track = TranslationTrackInfo(translation, original, base_original, status, patch, self.repo.active_branch.name)
            tracks.append(track)

        return tracks
