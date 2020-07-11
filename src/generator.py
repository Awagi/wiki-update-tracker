import logging as log
from pathlib import Path
from os import makedirs
import fnmatch
from git import (
    Repo,
    Actor
)
from tracker import (
    TranslationGitFile,
    TranslationTrack,
    ToCreateTranslationTrack,
    ToInitTranslationTrack,
    UpToDateTranslationTrack
)


def translation_fnmatch(track, filters):
    """
    Tells whether the translation filename in the given track matches one of the fnmatch patterns in ``filters``.

    :param tracker.TranslationTrack track: a translation track
    :param filters: fnmatch patterns
    :type filters: list(str)
    :return: True if any of filters matches the translation filename in ``track``
    :rtype: bool
    """
    f = track.translation.path.name
    for fil in filters:
        if fnmatch.fnmatch(f, fil):
            return True
    return False


class GitUpdater:
    """
    Update git files on the repo according to tracked files.
    """
    def __init__(self, tracks, repo, committer, author, branch_name):
        """
        Checkouts to new branch if different than current in given repo.

        :param tracks: iterable of valid tracker.TranslationTrackInfo
        :type tracks: list(tracker.TranslationTrack)
        :param git.Repo repo: the git Repo on the system
        :param git.Actor committer: the committer
        :param git.Actor author: the commit author
        :param str branch: the new branch to push changes to, repo.active_branch.name for no checkout
        :raise TypeError: when tracks is not iterable
        :raise TypeError: when any of tracks is not an instance of TranslationTrack
        :raise TypeError: when repo is not an instance of git.Repo
        :raise TypeError: when committer is not an instance of git.Actor
        :raise TypeError: when author is not an instance of git.Actor
        :raise TypeError: when branch_name is not an instance of str
        """
        try:
            iter(tracks)
        except TypeError:
            raise TypeError("tracks is not iterable")
        for t in tracks:
            if not isinstance(t, TranslationTrack):
                raise TypeError("one of tracks is not an instance of TranslationTrack")
        if not isinstance(repo, Repo):
            raise TypeError("repo is not an instance of git.Repo")
        if not isinstance(committer, Actor):
            raise TypeError("committer is not an instance of git.Actor")
        if not isinstance(author, Actor):
            raise TypeError("author is not an instance of git.Actor")
        if not isinstance(branch_name, str):
            raise TypeError("branch_name is not an instance of str")

        self.tracks = tracks
        self.repo = repo
        self.committer = committer
        self.author = author
        self.starting_branch = self.repo.active_branch
        self.commits = []

        if self.starting_branch.name != branch_name:
            # base branch on current HEAD and checkout
            if branch_name not in self.repo.branches:
                # branch doesn't exist
                log.debug("Creating new branch '{}'".format(branch_name))
                new_branch = self.repo.create_head(branch_name)
            else:
                log.debug("Resetting branch '{}' to HEAD".format(branch_name))
                new_branch = self.repo.branches[branch_name]
                new_branch.commit = 'HEAD'
            log.debug("Checking out branch '{}'".format(branch_name))
            new_branch.checkout()

    def create_stubs(self, commit_msg, stub_template, filters=['*']):
        """
        Creates stub translation files for To Create translation tracks in registered tracks whose translation filename matches one of the filters.

        Registered tracks are then changed in the ``GitUpdater`` instance to have modified tracks elevated to To Initialize tracks (with its level of info), then returned.

        :param str commit_msg: git commit message for changes
        :param model.StubTemplate stub_template: the content of the created stub file as template, which data is provided by a To Create track
        :param filters: fnmatch patterns used to filter To Create translation track, required to match the translation filename
        :type filters: list(str)
        :return: modified tracks with updated status (To Create tracks becoming To Init tracks, other tracks unchanged)
        :rtype: list(tracker.TranslationTrack)
        :raise RuntimeError: when tracks changed because of an external source after committing
        """
        indexes = []
        paths = []
        for i in range(len(self.tracks)):
            track = self.tracks[i]
            if isinstance(track, ToCreateTranslationTrack) and translation_fnmatch(track, filters):
                log.debug("Generating stub translation file {}".format(track.translation.path))
                paths.append(track.translation.path.as_posix())
                indexes.append(i)

                # format content with relative path to original file (from translation file directory)
                content = stub_template.format(track)

                # create dirs and file
                filepath = Path(self.repo.working_tree_dir) / track.translation.path
                makedirs(filepath.parent, exist_ok=True)
                with open(filepath, 'w') as f:
                    f.write(content)

        if len(paths) > 0:
            # add to index
            self.repo.index.add(paths)
            # git commit
            log.debug("Committing created stub files")
            commit = self.repo.index.commit(commit_msg, author=self.author, committer=self.committer)

            self.commits.append(commit)

            # udpate To Create tracks to To Initialize
            for i in indexes:
                track = self.tracks[i]
                if not (isinstance(track, ToCreateTranslationTrack) and translation_fnmatch(track, filters)):
                    raise RuntimeError("potential race condition detected, ensure you use everything sequentially")
                new_translation = TranslationGitFile(track.translation.path, track.translation.lang_tag, commit)
                new_track = ToInitTranslationTrack(new_translation, track.original, self.repo.active_branch.name)
                self.tracks[i] = new_track

        return self.tracks

    def create_copies(self, commit_msg, filters=['*']):
        """
        Creates copies from To Create track original files matching one of filters, into translation files.

        Registered tracks are then changed in the ``GitUpdater`` instance to have modified tracks elevated to Up-To-Date tracks (with its level of info), then returned.

        :param str commit_msg: git commit message for changes
        :param filters: fnmatch patterns
        :type filters: list(str)
        :return: all tracks containing modified tracks with updated status (To Create tracks become Up-To-Date tracks, others are unchanged)
        :rtype: list(tracker.TranslationTrack)
        :raise RuntimeError: when tracks changed because of an external source after committing
        """
        indexes = []
        paths = []
        for i in range(len(self.tracks)):
            track = self.tracks[i]
            if isinstance(track, ToCreateTranslationTrack) and translation_fnmatch(track, filters):
                log.debug("Creating copy from original file to translation file {}".format(track.translation.path))
                paths.append(track.translation.path.as_posix())
                indexes.append(i)

                # get content from original file
                content = track.original.blob.data_stream.read()

                # create dirs and translation file
                filepath = Path(self.repo.working_tree_dir) / track.translation.path
                makedirs(filepath.parent, exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(content)

        if len(paths) > 0:
            # add to index
            self.repo.index.add(paths)
            # git commit
            log.debug("Committing created stub files")
            commit = self.repo.index.commit(commit_msg, author=self.author, committer=self.committer)

            self.commits.append(commit)

            # update To Create tracks to Up-To-Date
            for i in indexes:
                track = self.tracks[i]
                if not (isinstance(track, ToCreateTranslationTrack) and translation_fnmatch(track, filters)):
                    raise RuntimeError("potential race condition detected, ensure you use everything sequentially")
                new_translation = TranslationGitFile(track.translation.path, track.translation.lang_tag, commit)
                new_track = UpToDateTranslationTrack(new_translation, track.original, self.repo.active_branch.name)
                self.tracks[i] = new_track

        return self.tracks

    def finish(self, force_push=False, pull_request=None):
        """
        Executes commit, push and checkout to starting branch.
        If ``pull_request`` is set, it will create a pull request to merge changed branch to starting branch if no such PR already exists and if changes were made.

        Generating a pull request requires the given GitHub Repository object to be initialized with a user or application having read/write permission on Pull requests.

        :param bool force_push: use "git push --force" instead of "git push" when True
        :param github.Repository.Repository pull_request: generate a pull request on the given repository if set
        :return: current (created or not) Pull request number, or None if not set
        :rtype: int or None
        """
        head_name = self.repo.active_branch.name

        # push if changes
        if len(self.commits) > 0:
            # git push
            log.debug("Pushing changes")
            origin = self.repo.remote(name='origin')
            if force_push:
                push = origin.push(refspec="refs/heads/{0}:refs/heads/{0}".format(head_name), force=True)
            else:
                push = origin.push(refspec="refs/heads/{0}:refs/heads/{0}".format(head_name))
            log.debug("Push response: {}".format(push[0].summary))

        if self.starting_branch != self.repo.active_branch:
            # checkout initial branch
            log.debug("Checking out starting branch '{}'".format(self.starting_branch.name))
            self.starting_branch.checkout()

            if pull_request is not None and len(self.commits) > 0:
                # make pull request after checking it doesn't exist already
                head_pr = "{}:{}".format(pull_request.owner.name, head_name)
                base_pr = self.starting_branch.name
                prs = pull_request.get_pulls(state="open", head=head_pr, base=base_pr)

                try:
                    pr = prs[0]
                except IndexError:
                    title_pr = "Generated translation stubs and copies"
                    body_pr = (
                        'As of WUT policy, translation stubs and copies were created. Please check added files before merging.\n'
                        '\n'
                        'Commits may be added to branch {} by WUT, you should merge this PR after merging PRs affecting original files and WUT is done.\n'
                        '\n'
                        '*Remember to leave the branch management to the GitHub Action only. Don\'t use it for other purposes.*\n'
                    ).format(head_name)
                    pr = pull_request.create_pull(title=title_pr, body=body_pr, head=head_pr, base=base_pr, maintainer_can_modify=True)
                return pr.number

        return None
