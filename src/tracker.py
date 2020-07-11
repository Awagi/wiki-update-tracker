from enum import Enum, unique
from constants import RFC5646_LANGUAGE_TAGS
# logs for debugging
import logging as log
# to read header in markdown through frontmatter
import frontmatter
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


@unique
class Status(str, Enum):
    """Indicates a translation has to be created."""
    TBC = "To Create"
    """Indicates a translation has to be initialized. A replacement stub exists with no translation."""
    TBI = "To Initialize"
    """Indicates a translation is up-to-date. It matches its corresponding original content."""
    UTD = "Up-To-Date"
    """Indicates a translation has to be updated. The corresponding original content changed."""
    Update = "To Update"
    """Indicates a translation is orphan, it has no corresponding original content."""
    Orphan = "Orphan"


class GitFile:
    """
    Defines a file and its last changes within a git repo.

    :var pathlib.Path path: its relative path within the git repo, must lead to a file
    :var bool no_trace: True if the file has no trace in git (according to given rev commit), False otherwise
    :var git.Commit commit: last commit modifying the file, None if ``no_trace``
    :var bool new_file: True if the file was newly created, False otherwise
    :var bool copied_file: True if the file was copied, False otherwise
    :var bool renamed_file: True if the file was renamed, False otherwise
    :var pathlib.Path rename_from: the old file path if ``renamed_file``, None otherwise
    :var pathlib.Path rename_to: the new file path if ``renamed_file``, None otherwise
    :var deleted_file: True if the file was deleted, False otherwise
    :var git.Blob blob: file blob representation, None if ``no_trace`` or ``deleted_file``
    """
    def __init__(self, path, commit):
        """
        Get file info for a file at given path and from given rev commit.

        The ``path`` attribute is subject to differ from the given path argument if the file was last renamed with a new filename.

        :param pathlib.Path path: the file path relative to git repo
        :param git.Commit commit: last commit to start tracing last changer commit and get diff from
        """
        # init default values
        self.path = path
        self.no_trace = True
        self.commit = None
        self.new_file = False
        self.copied_file = False
        self.renamed_file = False
        self.rename_from = None
        self.rename_to = None
        self.deleted_file = False
        self.blob = None
        # get last commit changing given path
        it = commit.repo.iter_commits(rev=commit, paths=path, max_count=1)
        try:
            self.commit = next(it)
            # get what last changed on file
            try:
                # get diff between parent and changer commit
                p = next(self.commit.iter_parents())
                diff = p.diff(self.commit, paths=path)[0]

                self.new_file = diff.new_file
                self.copied_file = diff.copied_file
                self.renamed_file = diff.renamed_file
                self.deleted_file = diff.deleted_file
                self.blob = diff.b_blob
                if self.renamed_file:
                    self.rename_from = Path(diff.rename_from)
                    self.rename_to = Path(diff.rename_to)
                    if self.rename_to != path.name:
                        # redefine path to new name
                        self.path = Path(diff.b_path)
                self.no_trace = False
            except StopIteration:
                # no parent (changer commit is root)
                self.new_file = True
            # for some reasons, diff may not initialize b_blob (when renamed especially), let's find it here if that's the case
            if not self.deleted_file and self.blob is None:
                self.blob = self.commit.tree[self.path.as_posix()]
        except StopIteration:
            # the path was not found in git
            self.no_trace = True

    def cnt_lines(self):
        """
        Count lines ('\n' separated) in ``self.blob``.

        :return: number of lines in blob
        :rtype: int
        :raise NotImplementedError: when the blob is not set, either no_trace or deleted_file
        :raise ValueError: when blob is invalid
        """
        if self.no_trace or self.deleted_file:
            raise NotImplementedError("blob is not set, can't count lines")
        try:
            data = self.blob.data_stream.read()
        except (AttributeError, IOError):
            raise ValueError("invalid blob to count lines from")
        return data.count(b"\n") + 1


class TranslationGitFile(GitFile):
    """
    Defines a translation file and its last changes within a git repo, containing attributes:

    :var str lang_tag: language tag / code like 'fr' or 'fr-FR', from RFC5646
    :var str language: equivalent language from lang_tag
    """
    def __init__(self, path, lang_tag, commit):
        super().__init__(path, commit)
        self.lang_tag = lang_tag

    def __setattr__(self, name, value):
        """
        Modified special method to include constraints for language:
            - can't change ``language`` directly
            - ``lang_tag`` must be valid according to RFC5646, and will change ``language`` accordingly
        """
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


class GitPatch:
    """
    Git patch between two files with different commits.

    :var str diff: literal git diff
    :var int additions: number of added lines
    :var int deletions: number of deleted lines
    :var int changes: total number of changes (additions + deletions)
    """
    def __init__(self, a_file, b_file):
        """
        Calculates a git diff from ``a_file`` to ``b_file``. Results to all instance variables set.

        :param GitFile a_file: the base file to start the diff
        :param GitFile b_file: the second file to end diff
        :raise ValueError: when no diff b_file.path doesn't exist between a_file.commit and b_file.commit
        """
        # get diff to get applied patch
        a_commit = a_file.commit
        b_commit = b_file.commit
        diffs = a_commit.diff(b_commit, paths=b_file.path, create_patch=True)
        try:
            diff = diffs[0]
        except IndexError:
            log.debug("Got base commit {} and new commit {}".format(a_commit, b_commit))
            raise ValueError("invalid files to diff, path between both revs")
        self.diff = diff.diff.decode(b_commit.encoding)
        # get additions, deletions and changes
        self.additions = diff.diff.count(b"\n+")
        self.deletions = diff.diff.count(b"\n-")
        self.changes = self.additions + self.deletions


class TranslationTrack:
    """
    A translation track, associating an original file and a translation file.

    :var TranslationGitFile translation: the translation file
    :var GitFile original: the latest (according to current commit) original file
    :var Status status: the status for the translation file
    :var str branch: name of the git branch where tracking was done
    """
    def __init__(self, translation, original, status, branch):
        if isinstance(translation, TranslationGitFile):
            self.translation = translation
        else:
            raise ValueError("translation must be an instance of TranslationGitFile")
        if isinstance(original, GitFile):
            self.original = original
        else:
            raise ValueError("original must be an instance of GitFile")
        if isinstance(status, Status):
            self.status = status
        else:
            raise ValueError("status must be an instance of Status")
        self.branch = branch


class ToCreateTranslationTrack(TranslationTrack):
    """
    **To Create** translation track. Variable status is set to ``Status.TBC``.

    :var int missing_lines: number of lines to translate from original files
    """
    def __init__(self, translation, original, branch):
        super().__init__(translation, original, Status.TBC, branch)
        self.missing_lines = self.original.cnt_lines()


class ToInitTranslationTrack(TranslationTrack):
    """
    **To Initialize** translation track. Variable status is set to ``Status.TBI``.

    :var int missing_lines: number of lines to translate from original files
    """
    def __init__(self, translation, original, branch):
        super().__init__(translation, original, Status.TBI, branch)
        self.missing_lines = self.original.cnt_lines()


class ToUpdateTranslationTrack(TranslationTrack):
    """
    **To Update** translation track. Variable status is set to ``Status.Update``.

    :var GitFile base_original: the original file the translation was based on
    :var GitPatch patch: patch / diff between the original file and base original file
    :var bool to_rename: True if translation file has not the same name as original file, False otherwise
    """
    def __init__(self, translation, original, branch):
        super().__init__(translation, original, Status.Update, branch)
        if translation.path.name != original.path.name:
            self.to_rename = True
        else:
            self.to_rename = False

        # setup base original file
        if original.renamed_file:
            bo_path = original.rename_from
        else:
            bo_path = original.path
        self.base_original = GitFile(bo_path, translation.commit)

        self.patch = GitPatch(self.base_original, original)


class UpToDateTranslationTrack(TranslationTrack):
    """
    **Up-To-Date** translation track. Status is set to ``Status.UTD``.
    """
    def __init__(self, translation, original, branch):
        super().__init__(translation, original, Status.UTD, branch)


class OrphanTranslationTrack(TranslationTrack):
    """
    **Orphan** translation track. Status is set to ``Status.Orphan``.

    :var bool deleted: True if the original file was deleted, False otherwise (i.e original never existed)
    :var int surplus_lines: number of lines in orphan translation
    """
    def __init__(self, translation, original, branch):
        super().__init__(translation, original, Status.Orphan, branch)

        self.deleted = self.original.deleted_file
        self.surplus_lines = self.translation.cnt_lines()


def fetch_files(path, filter_globs, ignore_globs=[]):
    """
    Fetch files matching filtering glob patterns, excluding those matching ignoring glob patterns, within a directory.

    :param pathlib.Path path: a valid directory path
    :param filter_globs: glob-like patterns for files to filter
    :type filter_globs: list(str)
    :param ignore_globs: glob-like patterns for files to ignore
    :type ignore_globs: list(str)
    :return: resulting paths
    :rtype: list(pathlib.Path)
    """
    files = []
    excludes = []
    log.debug("Seeking files in {} filtered with {} and ignoring {}".format(path, filter_globs, ignore_globs))
    for gi in ignore_globs:
        ex = glob.iglob(gi, recursive=True)
        excludes.extend([Path(n) for n in ex])
    for gf in filter_globs:
        fi = glob.iglob(gf, recursive=True)
        for n in fi:
            p = Path(n)
            if path in p.parents and p.is_file() and p not in excludes:
                files.append(p)
    return files


def replace_parent(path, parent, new_parent):
    """
    Forge a new path a parent path into a new parent path.

    Useful to get corresponding path from translation file to original file, or from original file to translation file.

    :param pathlib.Path path: the path to translate
    :param pathlib.Path parent: one of the path parents, to remove
    :param str new_parent: new path to inject in place of parent
    :return: forged path
    :rtype: pathlib.Path
    """
    parent_str = parent.as_posix()
    child_str = path.as_posix()
    child_suffix = child_str[len(parent_str):]  # includes first char '/' if path != parent
    return Path("{}{}".format(new_parent.as_posix(), child_suffix))


def get_blob(self, path, commit):
    """
    Get the blob at corresponding path from the given commit.

    :param pathlib.Path path: path relative to repo, leading to a file
    :param git.Commit commit: the commit to get the blob from
    :return: the corresponding blob instance or None if not found
    :rtype: git.Blob or None
    """
    try:
        return commit.tree[path.as_posix()]
    except KeyError:
        return None


def has_tbi_header(blob):
    """
    Determines whether the To Initialize header is within a given blob representation of a file.

    Currently it uses a frontmatter parser (work with yaml and markdown).
    The header, as key:value is defined in constants HEADER_TBI_KEY and HEADER_TBI_VALUE.

    :param git.Blob blob: blob to read
    :return: True if header exists as key:value in blob, False otherwise
    :rtype: bool
    :raise ValueError: when the blob is invalid
    """
    try:
        post = frontmatter.loads(blob.data_stream.read())
    except (AttributeError, IOError):
        raise ValueError("invalid blob to read header from")
    except UnicodeDecodeError:
        # not frontmatter type file
        return False
    return HEADER_TBI_KEY in post and post[HEADER_TBI_KEY] == HEADER_TBI_VALUE


class TranslationTracker:
    """
    Represents the tracking part of the script, checking existent/non existent translation files and diff when changes where applied to original file.
    """
    def __init__(self, git_repo):
        """
        Creates the tracker for the specified language (use the tag from RFC 5646) and link the preliminary setup git repo.

        :param git.Repo git_repo: the git repository
        """
        self.map = {}  # key: (translation Path, language tag), value: original Path
        self.repo = git_repo
        self.working_dir = Path(self.repo.git.working_dir)

    def abs_path(self, path):
        """
        Translates a relative path into an absolute path with git repository path as its parent, unless it's absolute already.

        :param pathlib.Path path: path relative to git repository path, or absolute path
        :return: an absolute path, either itself or with git repository path as parent
        :rtype: pathlib.Path
        """
        if not path.is_absolute():
            return Path(self.working_dir) / path
        return path

    def rel_path(self, path):
        """
        Translates an absolute path including git working dir as its parent into a relative path, unless it's relative already.

        :param pathlib.Path path: absolute path in git working dir, or relative path (from git working dir)
        :return: a path relative to git working dir or itself if already relative
        :rtype: pathlib.Path
        :raise ValueError: when path is absolute but working dir is not its parent
        """
        if path.is_absolute():
            return path.relative_to(self.working_dir)
        return path

    def abs_glob(self, glob):
        """
        Translates a relative glob (to repo) into an absolute glob pattern using git repository directory as parent.

        :param str glob: glob pattern relative to git repository
        :return: new glob pattern with git repository directory as prefix
        :rtype: str
        """
        return "{}/{}".format(self.working_dir.as_posix(), glob)

    def put(self, translation_path, original_path, lang_tag, original_ignore_globs=[], filter_globs=["**/*"]):
        """
        Puts a translation file in the tracker, and maps/remaps it to its reflected based original file or directory.

        Be a directory, every files within `original_path` will be added according to filter.
        Also, as directories, `original_path` and `translation_path` must have the same structure and filenames.

        Be a file, filter_globs and original_ignore_globs are irrelevant.

        :param pathlib.Path translation_path: a valid path relative to the git repo, different from `original_path`
        :param pathlib.Path original_path: a valid path relative to the git repo
        :param str lang_tag: the language tag from RFC 5646 to apply on this translation
        :param filter_globs: glob patterns relative to git repository to filter files to be tracked, defaults to all files
        :type filter_globs: list(str)
        :param original_ignore_globs: glob patterns relative to git repository to ignore matching files when browsing original directory
        :type original_ignore_globs: list(str)
        :raise SamePathException: when original and translation paths are the same
        :raise ValueError: when original_path is not a file nor a directory
        :raise LanguageTagException: when given language tag is not referenced in RFC 5646

        :example: With the following tree view in git repo:
        ```
        docs
        ├─ README.md
        ├─ nested
        │  └─ README.md
        └─ zh
           ├─ README.md
           └─ foo.md
        ```

        ``tracker.put(translation_path='docs/zh', original_path='docs', lang_tag='zh', original_ignore_globs=['docs/zh/**/*'], filter_globs=['**/*.md'])`` maps:
            - ``docs/zh/README.md`` to ``docs/README.md``
            - ``docs/zh/nested/README.md`` to ``docs/nested/README.md``
            - ``docs/zh/foo.md`` to ``docs/foo.md``
        """
        abs_translation_path = self.abs_path(translation_path)
        abs_original_path = self.abs_path(original_path)
        if abs_translation_path == abs_original_path:
            raise SamePathException()

        if abs_original_path.is_file():
            abs_originals = [abs_original_path]
            abs_translations = [abs_translation_path]
        elif abs_original_path.is_dir():
            # get every existing original files and translation files
            abs_ignore_globs = [self.abs_glob(gi) for gi in original_ignore_globs]
            abs_filter_globs = [self.abs_glob(gf) for gf in filter_globs]
            abs_originals = fetch_files(abs_original_path, abs_filter_globs, abs_ignore_globs)
            abs_translations = fetch_files(abs_translation_path, abs_filter_globs)
        else:
            log.debug("Got original path {}".format(abs_original_path))
            raise ValueError("original path is neither a file or a directory")

        # map translations to originals from found original paths and from found translation paths
        for abs_original in abs_originals:
            original = self.rel_path(abs_original)
            translation = replace_parent(original, original_path, translation_path)
            if (translation, lang_tag) not in self.map:
                self.map[translation, lang_tag] = original
                log.debug("Mapped translation file '{}' from original file '{}'".format(translation, original))
        for abs_translation in abs_translations:
            translation = self.rel_path(abs_translation)
            if (translation, lang_tag) not in self.map:
                original = replace_parent(translation, translation_path, original_path)
                self.map[translation, lang_tag] = original
                log.debug("Mapped translation file '{}' to original file '{}'".format(translation, original))

    def track(self):
        """
        Tracks mapped files (``put`` method), returning 1 TranslationTrack instance each.
        Provided data, especially status, is defined from the active commit in the repo.

        Basically, each translation file was last modified and included in a commit.
        Based on this commit, we take the original file and compare it to the same original file on the current commit to know whether it was modified or not.
        Returned translation status can be:
            - To Create (``Status.TBC``), returned as ``ToCreateTranslationTrack``
            - To Initializeto be initialized (``Status.TBI``), returned as ``ToInitTranslationTrack``
            - To Update (``Status.Update``), returned as ``ToUpdateTranslationTrack``
            - Up-To-Date (``Status.UTC``), returned as ``UpToDateTranslationTrack``
            - Orphan (``Status.Orphan``), returned as ``OrphanTranslationTrack``

        This assumes the translation was correctly done based on the original file from this commit, as this function does not parse contents or anything.

        :return: created tracks, typed as subclasses of ``TranslationTrack``
        :rtype: list(TranslationTrack)
        """
        tracks = []

        active_commit = self.repo.active_branch.commit
        branch_name = self.repo.active_branch.name
        for (translation_path, lang_tag), original_path in self.map.items():
            # SETUP file information
            original = GitFile(original_path, active_commit)
            translation = TranslationGitFile(translation_path, lang_tag, active_commit)

            if original.no_trace and translation.no_trace:
                # this is unexpected => some file found in put method is not in git
                log.warning("Some path doesn't appear in git, won't treat this one.")
                log.debug("Original file {} and translation file {} don't exist in commits. Are they in stage? Did the active HEAD changed during the script?".format(original.path, translation.path))
                continue
            elif original.no_trace or original.deleted_file:
                # original file either never existed or was removed
                track = OrphanTranslationTrack(translation, original, branch_name)
            elif translation.no_trace or translation.deleted_file:
                # translation file either never existed or was removed
                track = ToCreateTranslationTrack(translation, original, branch_name)
            elif has_tbi_header(translation.blob):
                # translation file has the explicit To Initialize header
                track = ToInitTranslationTrack(translation, original, branch_name)
            elif translation.commit == original.commit or original.commit in translation.commit.iter_parents():
                # translation is more recent than original
                track = UpToDateTranslationTrack(translation, original, branch_name)
            else:
                track = ToUpdateTranslationTrack(translation, original, branch_name)

            tracks.append(track)

        return tracks
