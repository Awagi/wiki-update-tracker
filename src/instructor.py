import logging as log
from tracker import (
    Status,
    TranslationTrack
)
from model import (
    GithubTemplate,
    GithubTemplater
)
from github import Repository
import fnmatch


class IssuesInstructor:
    """
    Updater for GitHub Issues. Uses ``model.GithubTemplate`` for templating according to provided GitHub Repository and translation tracks.

    REQUIRES the repo instance to be authenticated with a user with read/write access to issues.
    """
    def __init__(self, tracks, repo, label, title_template, body_templater):
        """
        Empty templates means no update.

        :param tracks: the translation tracks
        :type tracks: list(tracker.TranslationTrack)
        :param github.Repository.Repository repo: the Github repo with required permission on Issues and Projects
        :param str label: the GitHub label to update only issues holding it, shouldn't be empty
        :param model.GithubTemplate title_template: template defining the issue title for any translation track (``tracker.TranslationTrack``), must include a unique key such as t.translation.path
        :param model.GithubTemplater body_templater: templates mapped to statuses for issue bodies
        :raise TypeError: when tracks is not iterable
        :raise TypeError: when any of tracks is not an instance of TranslationTrack
        :raise TypeError: when repo is not an instance of github.Repository.Repository
        :raise TypeError: when title_template is not an instance of model.GithubTemplate
        :raise TypeError: when body_templater is not an instance of model.GithubTemplater
        :raise AttributeError: when title_template is empty
        """
        try:
            iter(tracks)
        except TypeError:
            raise TypeError("tracks is not iterable")
        for t in tracks:
            if not isinstance(t, TranslationTrack):
                raise TypeError("one of tracks is not an instance of TranslationTrack")
        if not isinstance(repo, Repository.Repository):
            raise TypeError("repo is not an instance of github.Repository.Repository")
        if not isinstance(title_template, GithubTemplate):
            raise TypeError("title_template is not an instance of GithubTemplate")
        if not isinstance(body_templater, GithubTemplater):
            raise TypeError("body_templater is not an instance of GithubTemplater")
        if title_template.empty:
            raise AttributeError("title_template can't be empty")

        self.tracks = tracks
        self.repo = repo
        self.label = label
        self.title = title_template
        self.body_templater = body_templater
        # map body templates to their equivalent status, with parameters for issues
        self.issue_policies = {
            Status.TBC: {
                "label": "translation:new",
                "state": "open"
            },
            Status.TBI: {
                "label": "translation:new",
                "state": "open"
            },
            Status.Update: {
                "label": "translation:update",
                "state": "open"
            },
            Status.UTD: {
                "label": "translation:ok",
                "state": "closed"
            },
            Status.Orphan: {
                "label": "translation:orphan",
                "state": "open"
            }
        }

    def instruct(self, filters=["*"]):
        """
        Update issues on Github according to the given tracked files, for translation files matching one of fnmatches (see https://docs.python.org/3/library/fnmatch.html).

        The idea is to have an issue per translation track, with the following policy per status:
            - To Create translation: open issue with "translation:new" label
            - To Init translation: open issue with "translation:new" label
            - To Update translation: open issue with "translation:update" label
            - Up-To-Date translation: closed issue with "translation:ok" label
            - Orphan translation: open issue with "translation:orphan" label

        Inexistent issues will be created, existent will be updated and duplicates (i.e with self.label and same title) will be removed.

        :param filters: fnmatch to filter translation file to instruct, such as '*.md' (not case-sensitive)
        :type filters: list(str)
        """
        # List issues from repository having the bot label
        log.debug("Fetch existing issues from Github")
        issues = self.repo.get_issues(state="all", labels=[self.label])

        subtracks = []
        for t in self.tracks:
            for pattern in filters:
                if fnmatch.fnmatch(t.translation.path.name, pattern):
                    subtracks.append(t)
                    break
        log.debug("Instructing {} issues out of {} total tracks (filtered by filename)".format(len(subtracks), len(self.tracks)))

        ret = []  # store updated and created open issue numbers
        total = len(subtracks)
        cnt = 0
        for track in subtracks:
            cnt = cnt + 1
            policy = self.issue_policies[track.status]

            if track.status in self.body_templater:
                title = self.title.format(track, self.repo)
                body = self.body_templater.format(track, self.repo)
                label = policy["label"]
                state = policy["state"]
                log.info("[{}/{}] Instructing issue for {}".format(cnt, total, track.translation.path))
            else:
                # issue body template is not defined for current track status, then no update required here
                log.info("[{}/{}] Skipping {}: template undefined for {} status".format(cnt, total, track.translation.path, track.status))
                continue

            issue_finder = (issue for issue in issues if issue.title == title)
            issue = next(issue_finder, None)

            if issue is None:
                log.debug("File {} doesn't have an existing issue, creating it".format(track.translation.path))
                issue = self.repo.create_issue(title=title, body=body, labels=[self.label, label])
                log.debug("Successfully created issue #{}".format(issue.number))
                # closing the created issue afterward if state to 'closed'
                if state == "closed":
                    issue.edit(state=state)
            else:
                # removing duplicate issues if found (with similar title and label)
                for duplicate in issue_finder:
                    log.debug("Found duplicate issue #{}, marking and closing it".format(duplicate.number))
                    duplicate.edit(labels=["duplicate"], state="closed")
                log.debug("Found issue #{} for file {}, updating it".format(issue.number, track.translation.path))
                issue.edit(title=title, body=body, labels=[self.label, label], state=state)

            if state == "open":
                ret.append(issue.number)

        return ret


class ProjectsInstructor:
    """
    Updater for GitHub Projects. Uses ``model.GithubTemplate`` for templating according to provided GitHub Repository and translation tracks.

    REQUIRES the repo instance to be authenticated with a user with read/write access to projects.
    """
    def __init__(self, tracks, repo, title_template, column_templater, card_templater, body_template=GithubTemplate()):
        """
        Instanciates the updater with necessary templates and the templaters defining which template to use when encountering different statuses.

        Templaters are used to create and update columns and cards in the project more finely according to the status.
        Say for a To Update track status, if a template is defined in the column templater, it will create it (when calling the ``update`` method).

        If no column template is set for a specific status in ``column_templater``, no card will be created, even if it is set in ``card_templater`` as it is dependent of a column.

        :param tracks: the translation tracks
        :type tracks: list(tracker.TranslationTrack)
        :param github.Repository repo: the Github repo with required permission on Issues and Projects
        :param model.GithubTemplate title_template: template defining the project title for any translation track (``tracker.TranslationTrack``), can't be empty
        :param model.GithubTemplater column_templater: templates mapped to statuses for column creations
        :param model.GithubTemplater card_templater: templates mapped to statuses for card updates and creations, every templates must format to a unique card (e.g contain translation path as key)
        :param model.GithubTemplate body_template: template defining the body description of a project, when it is created
        :raise TypeError: when tracks is not iterable
        :raise TypeError: when any of tracks is not an instance of TranslationTrack
        :raise TypeError: when repo is not an instance of github.Repository.Repository
        :raise TypeError: when title_template is not an instance of model.GithubTemplate
        :raise TypeError: when column_templater is not an instance of model.GithubTemplater
        :raise TypeError: when card_templater is not an instance of model.GithubTemplater
        :raise TypeError: when body_template is not an instance of model.GithubTemplate
        :raise AttributeError: when title_template is empty
        """
        try:
            iter(tracks)
        except TypeError:
            raise TypeError("tracks is not iterable")
        for t in tracks:
            if not isinstance(t, TranslationTrack):
                raise TypeError("one of tracks is not an instance of TranslationTrack")
        if not isinstance(repo, Repository.Repository):
            raise TypeError("repo is not an instance of github.Repository.Repository")
        if not isinstance(title_template, GithubTemplate):
            raise TypeError("title_template is not an instance of GithubTemplate")
        if not isinstance(column_templater, GithubTemplater):
            raise TypeError("column_templater is not an instance of GithubTemplater")
        if not isinstance(card_templater, GithubTemplater):
            raise TypeError("card_templater is not an instance of GithubTemplater")
        if not isinstance(body_template, GithubTemplate):
            raise TypeError("body_template is not an instance of GithubTemplate")
        if title_template.empty:
            raise AttributeError("title_template can't be empty")

        self.tracks = tracks
        self.repo = repo
        self.title = title_template
        self.body = body_template
        self.column_templater = column_templater
        self.card_templater = card_templater

        # cached projects as {project1_id: {"project": project1, "columns": [column1_id, column2_id]}}
        self.projects = None
        # cached columns as {column1_id: {"column": column1, cards: [card1_id, card2_id]}}
        self.columns = {}
        # cached cards as {card1_id: {"card": card1, "processed": True}}
        self.cards = {}

    def obtain_project(self, title, body):
        """
        Gets or creates a project in GitHub repository Projects.
        First time this method is called, it will fetch every projects and cache them.
        If no project matching the given title is found, a new one will be created and cached with this title and given body.

        :param str title: the title of the project, as key to find project
        :param str body: the body description of the project, only used when project is created
        :return: the project matching given title
        :rtype: github.Project
        """
        if self.projects is None:
            # projects not cached, fetch them
            self.projects = dict((project.id, {"project": project, "columns": None}) for project in self.repo.get_projects())

        project_finder = (pcache["project"] for pcache in self.projects.values() if pcache["project"].name == title)
        project = next(project_finder, None)
        if project is None:
            # project doesn't exist in GitHub Projects, create it
            log.debug("Creating project '{}'".format(title))
            project = self.repo.create_project(title, body)
            self.projects[project.id] = {
                "project": project,
                "columns": None
            }

        return project

    def obtain_column(self, project, name):
        """
        Gets or creates a column in a project.
        First time this method is called, it will fetch every columns for this project and cache them.
        If no column matching the given name is found, a new one will be created and cached with this name.

        :param github.Project project: the project to fetch columns and create new one if necessary
        :param str name: the name of the column, as key to find column
        :return: the column matching given name
        :rtype: github.ProjectColumn
        """
        pcache = self.projects[project.id]
        if pcache["columns"] is None:
            # columns from given project not cached, fetch them
            pcache["columns"] = []
            for column in project.get_columns():
                self.columns[column.id] = {
                    "column": column,
                    "cards": None
                }
                pcache["columns"].append(column.id)

        column_finder = (self.columns[col_id]["column"] for col_id in pcache["columns"] if self.columns[col_id]["column"].name == name)
        column = next(column_finder, None)
        if column is None:
            # column doesn't exist in the project in GitHub, create it
            log.debug("Creating column '{}'".format(name))
            column = project.create_column(name)
            self.columns[column.id] = {
                "column": column,
                "cards": None
            }
            pcache["columns"].append(column.id)

        return column

    def update_card(self, column, key, note):
        """
        Gets and updates, or creates a card from a project column.
        First time this method is called, it will fetch every cards in the given column and cache them.
        The card is found using the key, which is a substring within the note. This key must be unique.
        The card is either untouched, updated or created, then left as processed (in ``self.cards``).

        :param github.ProjectColumn column: the column in the project to fetch cards
        :param str key: key in note, a unique substring such as the translation file path
        :param str note: the new note to put in the card, which should also contain the key
        :return: cards in the column
        :rtype: list(github.ProjectCard)
        """
        ccache = self.columns[column.id]
        if ccache["cards"] is None:
            # cards from given project column not cached, fetch them
            ccache["cards"] = []
            for card in column.get_cards(archived_state='not_archived'):
                self.cards[card.id] = {
                    "card": card,
                    "processed": False
                }
                ccache["cards"].append(card.id)

        card_finder = (self.cards[card_id]["card"] for card_id in ccache["cards"] if key in self.cards[card_id]["card"].note)
        card = next(card_finder, None)
        if card is None:
            # card doesn't exist in the column, create it
            log.debug("Creating new card '{}' in column '{}'".format(key, column.name))
            card = column.create_card(note=note)
            self.cards[card.id] = {
                "card": card
            }
            ccache["cards"].append(card.id)
        elif card.note != note:
            log.debug("Editing card '{}' in column '{}'".format(key, column.name))
            card.edit(note=note)
        self.cards[card.id]["processed"] = True

        return card

    def instruct(self, filters=["*"]):
        """
        Update Projects on Github according to the given tracked files and for translation files matching one of fnmatches (see https://docs.python.org/3/library/fnmatch.html).

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

        :param filters: fnmatch to filter translation file to instruct, such as '*.md' (not case-sensitive)
        :type filters: list(str)
        """
        subtracks = []
        for t in self.tracks:
            for pattern in filters:
                if fnmatch.fnmatch(t.translation.path.name, pattern):
                    subtracks.append(t)
                    break
        log.debug("Instructing {} issues out of {} total tracks (filtered by filename)".format(len(subtracks), len(self.tracks)))

        total = len(subtracks)
        cnt = 0
        for track in subtracks:
            cnt = cnt + 1
            # format project title and columns templates according to current track
            if track.status in self.column_templater and track.status in self.card_templater:
                column_name = self.column_templater.format(track, self.repo)
                card_note = self.card_templater.format(track, self.repo)
                title = self.title.format(track, self.repo)
                body = self.body.format(track, self.repo)
                log.info("[{}/{}] Instructing card {} in project {}".format(cnt, total, track.translation.path, title))
            else:
                # column or card template is not defined for current track status, then no update required here
                log.info("[{}/{}] Skipping {}: template undefined for {} status".format(cnt, total, track.translation.path, track.status))
                continue

            project = self.obtain_project(title, body)
            column = self.obtain_column(project, column_name)
            self.update_card(column, track.translation.path.as_posix(), card_note)

        # archiving unprocessed cached cards
        for cache_card in self.cards.values():
            if not cache_card["processed"]:
                log.debug("Archiving duplicate, obsolete or user-created card")
                cache_card["card"].edit(archived=True)
