from github_utils import file_url, raw_file_url, compare_url
from tracker import Status
import logging as log
import os


class TemplateInfo:
    """
    Contains info for the updater templates, such as:
        - `language`: language for current translation, provided in TBC, TBI, Update, UTD (Updater)
        - `lang_tag`: language tag for current translation, as of RFC 5646, provided in TBC, TBI, Update, UTD (Updater)
        - `translation_filename`: filename of translation file, provided in TBC, TBI, Update, UTD (Updater)
        - `original_filename`: filename of original file, provided in TBC, TBI, Update, UTD (Updater)
        - `base_original_filename`: filename of base original file, provided in TBC, TBI, Update, UTD (Updater)
        - `translation_path`: translation file path, provided in TBC, TBI, Update, UTD (Updater)
        - `original_path`: original file path, provided in TBC, TBI, Update, UTD (Updater)
        - `original_commit`: original commit sha, provided in TBC, TBI, Update, UTD (Updater)
        - `translation_url`: Github URL to translation file (using branch rev), provided in TBC, TBI, Update, UTD (GithubUpdater)
        - `original_url`: Github URL to original file (using commit rev), provided in TBC, TBI, Update, UTD (GithubUpdater)
        - `raw_original_url`: Github URL to raw original file (using commit rev), provided in TBC, TBI, Update, UTD (GithubUpdater)
        - `translation_commit`: translation commit sha, provided in TBI, Update, UTD (Updater)
        - `raw_translation_url`: Github URL to raw translation file (using commit rev), provided in TBI, Update, UTD (GithubUpdater)
        - `base_original_url`: Github URL to base original file (using commit rev), provided in Update (GithubUpdater)
        - `raw_base_original_url`: Github URL to raw base original file (using commit rev), provided in Update (GithubUpdater)
        - `compare_url`: Github URL to Github comparison (using base_original and original commit rev), provided in Update (GithubUpdater)
        - `patch_diff`: the git diff str comparison, provided in Update (Updater)
        - `patch_additions`: git diff number of lines added, provided in TBC, TBI, Update, UTD (Updater)
        - `patch_deletions`: git diff number of lines deleted, provided in Update (Updater)
        - `patch_changes`: git diff number of lines changes (additions + deletions), provided in Update (Updater)
        - `translation_to_original_path`: local relative link from translation file parent directory to original file, provided in TBC, TBI, Update, UTD (Updater)
    """
    def __init__(self):
        self.language = ""
        self.lang_tag = ""
        self.translation_filename = ""
        self.original_filename = ""
        self.base_original_filename = ""
        self.translation_path = ""
        self.translation_commit = ""
        self.original_path = ""
        self.original_commit = ""
        self.translation_url = ""
        self.original_url = ""
        self.compare_url = ""
        self.raw_translation_url = ""
        self.raw_original_url = ""
        self.base_original_url = ""
        self.raw_base_original_url = ""
        self.patch_diff = ""
        self.patch_additions = 0
        self.patch_deletions = 0
        self.patch_changes = 0
        self.translation_to_original_path = ""


class UpdaterTemplate:
    """
    Represents a template. Like "{t.language} translation needs to be done here: {t.translation_url}"
    """
    def __init__(self, template):
        """
        Template is a str with unformatted tags of a `t` object representing `TemplateInfo`, which will be provided by `GithubUpdater` to then format Issues and Projects.

        :param template: unformatted str, with `format`-type tags using `t`, instance of `TemplateInfo`
        """
        self.template = template

    def format(self, info):
        """
        Format the template using the TemplateInfo given, resources for the template to be built.

        :param info: a valid instance of TemplateInfo
        :return: the formatted message, str
        """
        return self.template.format(t=info)


class Updater:
    """
    Update using templates based on a list of tracker.TranslationTracker.
    """
    def __init__(self, tracks):
        """
        :param tracks: iterable of valide tracker.TranslationTrackInfo
        """
        self.tracks = tracks
        self.update_info()

    def update_info(self):
        """
        Update `self.template_info` using tracks.
        """
        # providing template data for every tracks
        self.template_info = {}
        for track in self.tracks:
            tinfo = TemplateInfo()
            if track.status in [Status.TBC, Status.TBI, Status.Update, Status.UTD]:
                tinfo.language = track.translation.language
                tinfo.lang_tag = track.translation.lang_tag
                tinfo.translation_filename = os.path.split(track.translation.path)[1]
                tinfo.original_filename = os.path.split(track.original.path)[1]
                tinfo.base_original_filename = os.path.split(track.base_original.path)[1]
                tinfo.translation_path = track.translation.path
                tinfo.original_path = track.original.path
                tinfo.original_commit = track.original.commit.hexsha
                tinfo.patch_additions = track.patch.additions
                translation_dir = os.path.split(track.translation.path)[0]
                tinfo.translation_to_original_path = '/'.join(os.path.relpath(track.original.path, translation_dir).split(os.sep))
            if track.status in [Status.TBI, Status.Update, Status.UTD]:
                tinfo.translation_commit = track.translation.commit.hexsha
            if track.status is Status.Update:
                tinfo.patch_diff = track.patch.diff
                tinfo.patch_deletions = track.patch.deletions
                tinfo.patch_changes = track.patch.changes
            self.template_info[track] = tinfo


class GitUpdater(Updater):
    """
    Update git files on the system according to tracked files from tracker.TranslationTracker.
    """
    def __init__(self, tracks, repo, committer, author):
        """
        :param repo: the git Repo on the system
        :param tracks: iterable of valid tracker.TranslationTrackInfo
        :param committer: the committer, instance of Actor
        :param author: the commit author, instance of Actor
        """
        super().__init__(tracks)
        self.repo = repo
        self.committer = committer
        self.author = author
        self.update_info()

    def create_stubs(self, commit_msg, stub_content_template):
        """
        Automatically create, commit and push stub translation files with the header `translation-done: false` for To Be Created ones (when status is Status.TBC).

        Useful when adding new language to the job, and to get notified when a new original page is created.

        Tracks are automatically updated from status TBC to status TBI when a stub is created. The list won't contain TBC tracks anymore.

        :param commit_msg: str, git commit message for changes
        :param stub_content_template: instance of UpdaterTemplate, the content of the created stub file
        """
        paths = []
        for track in self.tracks:
            tinfo = self.template_info[track]
            if track.status is Status.TBC:
                log.debug("Generating stub translation file {}".format(track.translation.path))
                paths.append(track.translation.path)

                # format content with relative path to original file (from translation file directory)
                content = stub_content_template.format(tinfo)

                # create dirs and file
                filepath = os.path.join(self.repo.working_tree_dir, os.sep.join(track.translation.path.split('/')))
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w') as f:
                    f.write(content)

        if len(paths) > 0:
            # add to index
            self.repo.index.add(paths)
            # git commit
            log.debug("Committing created stub files")
            commit = self.repo.index.commit(commit_msg, author=self.author, committer=self.committer)

            # git push
            log.debug("Pushing changes")
            origin = self.repo.remote(name='origin')
            push = origin.push(force=True)
            log.debug("Push response: {}".format(push[0].summary))

            # putting TBC to same level of info than TBI
            for track in self.tracks:
                if track.status is Status.TBC:
                    track.status = Status.TBI
                    track.translation.blob = commit.tree[track.translation.path]
                    track.translation.commit = commit
            self.update_info()


class GithubUpdater(Updater):
    """
    Update Issues and/or Projects according to tracked files from tracker.TranslationTracker.
    Provides more info than Updater, like several links based on the repo.
    """
    def __init__(self, tracks, repo):
        """
        :param repo: the Github repo with enough permission on Issues and Projects
        :param tracks: iterable of valid tracker.TranslationTrackInfo
        """
        self.repo = repo
        super().__init__(tracks)

    def update_info(self):
        super().update_info()
        for track in self.tracks:
            if track.status in [Status.TBC, Status.TBI, Status.Update, Status.UTD]:
                self.template_info[track].translation_url = file_url(self.repo.full_name, track.branch, track.translation.path)
                self.template_info[track].original_url = file_url(self.repo.full_name, track.original.commit.hexsha, track.original.path)
                self.template_info[track].raw_original_url = raw_file_url(self.repo.full_name, track.original.commit.hexsha, track.original.path)
            if track.status in [Status.TBI, Status.Update, Status.UTD]:
                self.template_info[track].raw_translation_url = raw_file_url(self.repo.full_name, track.translation.commit.hexsha, track.translation.path)
            if track.status is Status.Update:
                self.template_info[track].base_original_url = file_url(self.repo.full_name, track.base_original.commit.hexsha, track.base_original.path)
                self.template_info[track].raw_base_original_url = raw_file_url(self.repo.full_name, track.base_original.commit.hexsha, track.base_original.path)
                self.template_info[track].compare_url = compare_url(self.repo.full_name, track.base_original.commit.hexsha, track.original.commit.hexsha)

    def update_issues(self, bot_label, title_template, tbc_template, tbi_template, update_template, utd_template):
        """
        Update issues on Github according to the given tracked files.

        The idea is to have an issue per translation page to track:
            - open issues for translated pages to update, to create and to initialize
            - closed issues for up-to-date translated pages

        REQUIRES the Github App to have read/write access to issues.

        :param bot_label: the bot Github label placed on issues to update when the script creates these
        :param title_template: instance of UpdaterTemplate, template for the title of every issues => USED AS IDENTIFIER with bot_label
        :param tbc_template: instance of UpdaterTemplate, template for To Be Created translations issue body
        :param tbi_template: instance of UpdaterTemplate, template for To Be Initialized translations issue body
        :param update_template: instance of UpdaterTemplate, template for To Update translations issue body
        :param utd_template: instance of UpdaterTemplate, template for Up-To-Date translations issue body
        :return: the list of open issues
        """
        # List issues from repository having the bot label
        log.debug("Fetch existing issues from Github")

        issues = self.repo.get_issues(state="all", labels=[bot_label])

        ret = []  # store updated and created open issue numbers
        total = len(self.tracks)
        cnt = 0
        for track in self.tracks:
            cnt = cnt + 1
            log.info("[{}/{}] Updating issue for {}".format(cnt, total, track.translation.path))
            tinfo = self.template_info[track]

            if track.status is Status.Update:
                body = update_template.format(tinfo)
                label = "translation:update"
                state = "open"
            elif track.status is Status.TBI:
                body = tbi_template.format(tinfo)
                label = "translation:new"
                state = "open"
            elif track.status is Status.TBC:
                body = tbc_template.format(tinfo)
                label = "translation:new"
                state = "open"
            elif track.status is Status.UTD:
                body = update_template.format(tinfo)
                label = "translation:ok"
                state = "closed"

            title = title_template.format(tinfo)
            issue_finder = (issue for issue in issues if issue.title == title)
            issue = next(issue_finder, None)

            if issue is None:
                log.debug("File {} doesn't have an existing issue, creating it".format(track.translation.path))
                issue = self.repo.create_issue(title=title, body=body, labels=[bot_label, label])
                log.debug("Successfully created issue {}".format(issue.number))
                # closing the created issue afterward if state to 'closed'
                if state == "closed":
                    issue.edit(state=state)
            else:
                for duplicate in issue_finder:
                    log.debug("Found duplicate issue {}, marking and closing it".format(duplicate.number))
                    duplicate.edit(labels=["duplicate"], state="closed")
                log.debug("Found issue for file {}, updating it".format(track.translation.path))
                issue.edit(title=title, body=body, labels=[bot_label, label], state=state)

            if state == "open":
                ret.append(issue.number)

        return ret

    def update_projects(self, title_template, body_template, tbc_column_template, tbi_column_template, update_column_template, utd_column_template, tbc_card_template, tbi_card_template, update_card_template, utd_card_template):
        """
        Update Projects on Github according to the given tracked files.

        1 Project per language or other (defined via title_template), with:
            - 1 column tbc_column
            - 1 column tbi_column
            - 1 column update_column
            - 1 column utd_column
        Columns can be merged.
        For example if tbc_column == tbi_column, there will be 1 column for both and 3 in total in the project (regardless of possible user-created columns, which remain untouched).

        A translation card is identified with the translation path. 1 unarchived card per translation is kept, moved and updated accordingly.
        Hence, every templates for cards should include "{t.translation_path}" in order for the script to update cards correctly.
        Otherwise it will create cards then remove older cards, leading to the same result but doubling process time and API calls.

        Duplicate cards and any other card not processed here found in seen columns are archived. You can still manually create and use cards in other columns in these projects.

        :param title_template: instance of UpdaterTemplate, template for the title for a project => USED AS IDENTIFIER with tag language
        :param body_template: instance of UpdaterTemplate, template for the body description of a project, when it is created
        :param tbc_column_template: instance of UpdaterTemplate, the column name for To Be Created translations in the project
        :param tbi_column_template: instance of UpdaterTemplate, the column name for To Be Initialized translations in the project
        :param update_column_template: instance of UpdaterTemplate, the column name for To Update translations in the project
        :param utd_column_template: instance of UpdaterTemplate, the column name for Up-To-Date translations in the project
        :param tbc_card_template: instance of UpdaterTemplate, template for To Be Created translations card note
        :param tbi_card_template: instance of UpdaterTemplate, template for To Be Initialized translations card note
        :param update_card_template: instance of UpdaterTemplate, template for To Update translations card note
        :param utd_card_template: instance of UpdaterTemplate, template for Up-To-Date translations card note
        """
        # initialize Projects: get or create project for every languages, then get or create every columns
        projects = list(self.repo.get_projects())
        project_columns = {}
        column_cards = {}
        total = len(self.tracks)
        cnt = 0
        for track in self.tracks:
            cnt = cnt + 1
            tinfo = self.template_info[track]

            title = title_template.format(tinfo)
            tbc_column_name = tbc_column_template.format(tinfo)
            tbi_column_name = tbi_column_template.format(tinfo)
            update_column_name = update_column_template.format(tinfo)
            utd_column_name = utd_column_template.format(tinfo)

            log.info("[{}/{}] Updating card {} in project {}".format(cnt, total, track.translation.path, title))

            project = next((project for project in projects if project.name == title), None)
            if project is None or project.name not in project_columns:
                # project doesn't exist locally
                if project is None:
                    # project doesn't exist remotely, create project then columns
                    log.debug("Creating project '{}'".format(title))
                    project = self.repo.create_project(title, body_template.format(tinfo))
                    projects.append(project)
                    existing_columns = []
                else:
                    # project exists remotely, fetch columns remotely then create when not found
                    existing_columns = list(project.get_columns())
                project_columns[project.name] = []
                for column_name in [tbc_column_name, tbi_column_name, update_column_name, utd_column_name]:
                    column = next((column for column in existing_columns + project_columns[project.name] if column.name == column_name), None)
                    if column is None:
                        log.debug("Creating column '{}'".format(column_name))
                        column = project.create_column(column_name)
                    project_columns[project.name].append(column)

            tbc, tbi, update, utd = project_columns[project.name]

            # build new card notes and get destination column
            if track.status is Status.Update:
                dest_column = update
                note = update_card_template.format(tinfo)
            elif track.status is Status.TBI:
                dest_column = tbi
                note = tbi_card_template.format(tinfo)
            elif track.status is Status.TBC:
                dest_column = tbc
                note = tbc_card_template.format(tinfo)
            elif track.status is Status.UTD:
                dest_column = utd
                note = utd_card_template.format(tinfo)

            cards = []
            for column in [tbc, tbi, update, utd]:
                key = project.name + column.name
                if key not in column_cards:
                    # necessary to fetch cards remotely
                    column_cards[key] = list(column.get_cards(archived_state='not_archived'))
                cards.extend(column_cards[key])
            # seek existing card for current track
            # Assuming it's sufficient, the identifier in every columns is the translation file path
            card_finder = (card for card in cards if track.translation.path in card.note)
            card = next(card_finder, None)

            # update or create card
            if card is None:
                # card does not exist, create it
                old_status = None
                log.debug("Creating new card '{}' in column '{}'".format(track.translation.path, dest_column.name))
                dest_column.create_card(note=note)
            else:
                # card exists, edit it and move it if necessary
                for column, status in [(utd, Status.UTD), (update, Status.Update), (tbi, Status.TBI), (tbc, Status.TBC)]:
                    key = project.name + column.name
                    if card in column_cards[key]:
                        old_status = status
                        # this card is being processed, remove it from list of unprocessed
                        column_cards[project.name + column.name].remove(card)
                if track.status != old_status:
                    # move card
                    log.debug("Moving card '{}' from {} to {}".format(track.translation.path, old_status, track.status))
                    card.move('top', dest_column)
                if card.note != note:
                    # edit card
                    log.debug("Editing card '{}'".format(track.translation.path))
                    card.edit(note=note)

        # archiving unprocessed cards in every columns
        for project_name, columns in project_columns.items():
            for column in columns:
                for card in column_cards[project_name + column.name]:
                    log.debug("Archiving duplicate, obsolete or user-created card from project {}, column {}".format(project_name, column.name))
                    card.edit(archived=True)
