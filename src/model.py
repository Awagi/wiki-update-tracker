from tracker import (
    GitFile,
    TranslationGitFile,
    GitPatch,
    TranslationTrack,
    ToCreateTranslationTrack,
    ToInitTranslationTrack,
    ToUpdateTranslationTrack,
    UpToDateTranslationTrack,
    OrphanTranslationTrack,
    Status
)
from pathlib import Path
import os.path
from github_utils import (
    file_url,
    raw_file_url,
    compare_url
)


class GitFileModel:
    """
    A model describing a git file.
    """
    def __init__(self, git_file):
        """
        Builds the model for templating after the given git file.

        :param tracker.GitFile git_file: git file to build the model from
        :raise ValueError: when git_file is not an instance of GitFile
        """
        if isinstance(git_file, GitFile):
            self.path = git_file.path.as_posix()
            self.filename = git_file.path.name
            self.directory = git_file.path.parent.as_posix()
            self.no_trace = git_file.no_trace
            if git_file.no_trace:
                self.commit = None
            else:
                self.commit = git_file.commit.hexsha
            self.new_file = git_file.new_file
            self.copied_file = git_file.copied_file
            self.renamed_file = git_file.renamed_file
            if git_file.rename_from:
                self.rename_from = git_file.rename_from.as_posix()
            else:
                self.rename_from = None
            if git_file.rename_to:
                self.rename_to = git_file.rename_to.as_posix()
            else:
                self.rename_to = None
            self.deleted_file = git_file.deleted_file
            if isinstance(git_file, TranslationGitFile):
                self.lang_tag = git_file.lang_tag
                self.language = git_file.language
        else:
            raise ValueError("git_file is not an instance of GitFile")


class GitPatchModel:
    """
    A model describing a git patch.
    """
    def __init__(self, git_patch):
        """
        Builds the model for templating after the given git patch.

        :param tracker.GitPatch git_patch: git patch to build the model from
        :raise ValueError: when git_patch is not an instance of GitPatch
        """
        if isinstance(git_patch, GitPatch):
            self.diff = git_patch.diff
            self.additions = git_patch.additions
            self.deletions = git_patch.deletions
            self.changes = git_patch.changes
        else:
            raise ValueError("git_patch is not an instance of GitPatch")


class TranslationTrackModel:
    """
    A model describing a translation track as an interface for templates to use.
    """
    def __init__(self, track):
        """
        Builds the model for templating after the given track.

        :param tracker.TranslationTrack: the track
        :raise ValueError: when track is not an instance of TranslationTrack
        """
        if isinstance(track, TranslationTrack):
            self.translation = GitFileModel(track.translation)
            self.original = GitFileModel(track.original)
            self.status = track.status
            if isinstance(track, ToCreateTranslationTrack):
                self.missing_lines = track.missing_lines
            elif isinstance(track, ToInitTranslationTrack):
                self.missing_lines = track.missing_lines
            elif isinstance(track, ToUpdateTranslationTrack):
                self.base_original = GitFileModel(track.base_original)
                self.patch = GitPatchModel(track.patch)
                self.to_rename = track.to_rename
            elif isinstance(track, UpToDateTranslationTrack):
                pass
            elif isinstance(track, OrphanTranslationTrack):
                self.deleted = track.deleted
                self.surplus_lines = track.surplus_lines
        else:
            raise ValueError("track is not an instance of TranslationTrack")


class Template:
    """
    Represents a template. Like "{t.translation.language} translation needs to be done here: {translation_url}" for a Github instruction, ``t`` being a TranslationTrackModel instance.

    :var str template: the template itself
    :var bool empty: whether the template is an empty string or not, generally meaning to an updater it should not process it
    """
    def __init__(self, template=""):
        """
        Template is a str with unformatted tags of a ``t`` object representing a ``TranslationTrackModel`` instance, and more args depending on the context (e.g URLs for Github).

        Creating an empty template would generally mean to an updater that it should not process it.

        :param str template: unformatted template, with ``format``-type tags using ``t``, instance of ``TranslationTrackModel``
        :raise TypeError: when template is not a str
        """
        if not isinstance(template, str):
            raise TypeError("template is not str")
        self.template = template
        self.empty = len(self.template) == 0

    def special_args(self, track, **kwargs):
        """
        Defines special arguments for the template from a track, when necessary.

        Override this method to provide special args when required in a certain context.

        :param tracker.TranslationTrack track: the track, base of template
        :param kwargs: other provided values for subclasses of this template when necessary
        :return: kwargs for template formatting
        :rtype: dict
        """
        return {}

    def format(self, t, **kwargs):
        """
        Format the template using the translation track given, resources for the template to be built.

        :param tracker.TranslationTrack t: a translation track or a subclass
        :param **kwargs: other parameters to pass when formatting specific template, defined in special_args of subclass
        :return: the formatted message
        :rtype: str
        :raise ValueError: when t is not a TranslationTrack instance
        """
        if not isinstance(t, TranslationTrack):
            raise ValueError("t is not a TranslationTrack instance")
        data = TranslationTrackModel(t)
        return self.template.format(t=data, **self.special_args(t, **kwargs))


class StubTemplate(Template):
    """
    Represents a template for content of stub files.
    """
    def special_args(self, track):
        """
        Sets special argument ``translation_to_original_path``, relative path to original file from translation parent directory.

        :param tracker.TranslationTrack track: the track, base of template
        :return: kwargs for template formatting
        :rtype: dict
        """
        return {
            "translation_to_original_path": Path(os.path.relpath(track.original.path, track.translation.track.parent)).as_posix()
        }


class GithubTemplate(Template):
    """
    Represents a template for Github Issues and Projects.
    """
    def special_args(self, track, repo):
        """
        Sets special arguments:
            - ``original_url``, Github URL to original file (using commit rev). Only with To Create, To Initialize, To Update and Up-To-Date tracks.
            - ``raw_original_url``, Github URL to raw original file (using commit rev). Only with To Create, To Initialize, To Update and Up-To-Date tracks.
            - ``translation_url``, Github URL to translation file (using branch rev). Only with To Initialize, To Update, Up-To-Date and Orphan tracks.
            - ``raw_translation_url``, Github URL to raw translation file (using commit rev). Only with To Initialize, To Update, Up-To-Date and Orphan tracks.
            - ``base_original_url``, Github URL to base original file (using commit rev). Only with To Update tracks.
            - ``raw_base_original_url``, Github URL to raw base original file (using commit rev). Only with To Update tracks.
            - ``compare_url``, Github URL to Github comparison (using base_original and original commit rev). Only with To Update tracks.

        :param tracker.TranslationTrack track: the track, base of template
        :param github.Repository.Repository repo: the github repo for URL building purpose
        :return: kwargs for template formatting
        :rtype: dict
        """
        args = {}
        if isinstance(track, (ToCreateTranslationTrack, ToInitTranslationTrack, ToUpdateTranslationTrack, UpToDateTranslationTrack)):
            args["original_url"] = file_url(repo.full_name, track.original.commit.hexsha, track.original.path.as_posix())
            args["raw_original_url"] = raw_file_url(repo.full_name, track.original.commit.hexsha, track.original.path.as_posix())
        if isinstance(track, (ToInitTranslationTrack, ToUpdateTranslationTrack, UpToDateTranslationTrack, OrphanTranslationTrack)):
            args["translation_url"] = file_url(repo.full_name, track.branch, track.translation.path.as_posix())
            args["raw_translation_url"] = raw_file_url(repo.full_name, track.translation.commit.hexsha, track.translation.path.as_posix())
        if isinstance(track, ToUpdateTranslationTrack):
            args["base_original_url"] = file_url(repo.full_name, track.base_original.commit.hexsha, track.base_original.path.as_posix()),
            args["raw_base_original_url"] = raw_file_url(repo.full_name, track.base_original.commit.hexsha, track.base_original.path.as_posix()),
            args["compare_url"] = compare_url(repo.full_name, track.base_original.commit.hexsha, track.original.commit.hexsha)
        return args

    def format(self, t, repo):
        return super().format(t, repo=repo)


class GithubTemplater:
    """
    Github Templates handler:
        - maps ``GithubTemplate`` instances to ``tracker.Status``
        - format corresponding template from ``tracker.TranslationTrack``, according to their status attribute
    """
    def __init__(self):
        self.map = {}

    def __setitem__(self, status, template):
        """
        Maps a template to a status. Templates can't be empty.

        :param tracker.Status status: the status to map the template to
        :param GithubTemplate template: the template to map to the status
        :raise TypeError: when status is not an instance of tracker.Status
        :raise TypeError: when template is not an instance of model.GithubTemplate
        :raise AttributeError: when template is empty
        """
        if not isinstance(template, GithubTemplate):
            raise TypeError("template is not an instance of GithubTemplate")
        if not isinstance(status, Status):
            raise TypeError("status is not an instance of Status")
        if template.empty:
            raise AttributeError("template can't be empty")
        self.map[status] = template

    def __contains__(self, status):
        """
        Tells whether a template is mapped to the given status.

        :param tracker.Status status: the status
        :return: True if status is key of a template, False otherwise
        :rtype: bool
        """
        return status in self.map

    def __getitem__(self, status):
        """
        Gets the template mapped to the given status.

        :param tracker.Status status: the status
        :return: the corresponding template, or None if status is not key of a template
        :rtype: GithubTemplate
        """
        if status in self:
            return self.map[status]
        else:
            return None

    def format(self, track, repo):
        """
        Gets the formatted template using the given translation track and corresponding to its status attribute.

        :param tracker.TranslationTrack: the track used as input to format the template
        :param github.Repository.Repository repo: the repo input for the GitHub template
        :return: the formatted template, or None if status is not mapped to a template
        :rtype: str
        :raise TypeError: when track is not an instance of tracker.TranslationTrack
        """
        if not isinstance(track, TranslationTrack):
            raise TypeError("track is not an instance of TranslationTrack")
        if track.status in self:
            return self.map[track.status].format(track, repo)
        else:
            return None
