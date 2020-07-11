# Update Tracker for Translations

Don't bother with your localisation when you make a change to an original file, let this Action automatically backtrack changes and instruct your translators for reflected changes on translation files through Github Issues or Github Projects.

> Currently, the Update Tracker Action purpose is to solely serve the [BSMG Wiki](https://github.com/beat-saber-modding-group/wiki), tracking updated English pages and notifying in issues/projects.
> As such, templates are specifically customized for a Wiki using vuepress i18n. It is currently being reviewed to work in more places and localisation structures.

## Overview

### Action features

The Update Tracker for Translations has 3 main features:
- **Backtracking**
    - Analyse commit history to provide status for translation files according to their corresponding original files.
- **Auto Generation**
    - Automatically create stubs or copy original for missing translation files, or remove orphan translation files. Either proposed in mergeable dedicated branch or directly to your main branch.
- **Instructing**
    - Instruct every changes in Github Issues and/or Projects, according to custom templates contextualized for each backtracked translation file.

Note that it does not parse file contents nor automatically translate. See [Assumptions](#Assumptions) .

### Translation file status

Tracked translation files can have one of these statuses:
1) **To Create**
    * The translation file doesn't exist where a corresponding original file does.
2) **To Initialize**
    * The translation file exists but does not contain translation yet.
3) **To Update**
    * The translation file was translated but the original file was edited thereafter.
4) **Up-To-Date**
    * The translation file was edited after or the same as its corresponding original file.
5) **Orphan**
    * The translation file exists but doesn't have a corresponding original file.

### Assumptions

For the system to work efficiently, these assumptions are made and should be respected:
- every translation folders have _the same tree view and filenames_ as the original folder
- when a translation file is edited, the translation is _always based on the most recent original file_.

## Changes

### New in v1.8

- New Orphan status when a translation file has no affiliated original file
- More control on templates: set them directly in the workflow file or in files
- Can now copy files (like images or videos)
- Control which files to track, and then to generate and instruct using glob and fnmatch patterns
- New feature to generate changes to another branch and making a pull request to merge to initial branch
- Better documentation I guess
- Code structure reviewed again along with better argument parsing
- **WARNING**: a lot of inputs were changed and new ones were added, check inputs below

### New in v1.7
- Github Projects is supported through input `update-projects`.
- Issues can now be enabled and disabled through input `update-issues`.
- Script much more stable and adaptable.
- **WARNING**: `translation-paths` was removed, because paths must now be given with corresponding language tags as described in new input `translations`.

### New in v1.6
- Update Tracker now automatically creates stub files when missing, with the correct header. Can be enabled or disabled in `auto-create` input.

### New in v1.5
- New comprehensive Frontmatter header `translation-done: false` to read from markdown or other Frontmatter compatible translation file automatically sets the status to TBI (To Be Initialized).

Example at the very beginning of a dummy file `example.md`:
```yml
---
translation-done: false
---
```

## Usage

Pre-requisite is a checked-out git repository set up on the active branch you want to track (use [checkout](https://github.com/actions/checkout)).

Then use this job in your workflow file:

```yml
- uses: Awagi/wiki-update-tracker@v1.8
  with:
    # The python script log level, either CRITICAL, ERROR, WARNING, INFO, DEBUG or NOTSET.
    # Change it for more or less verbosity in the Action.
    #
    # Not required. Default: 'INFO'.
    log-level: 'INFO'

    # 1) TRACKER

    # The local path of the checked-out git repository, make sure you checkout on the desired branch.
    #
    # REQUIRED.
    repo-path: '.'

    # Path to the directory containing original files, relative to repo-path.
    #
    # REQUIRED.
    original: 'docs'

    # Paths to the directories containing translation files, relative to repo-path, along with their associated language tag.
    # Language tag must respect RFC5646.
    #
    # REQUIRED.
    translations: |-
      fr:docs/fr
      cs:docs/cs

    # Glob patterns matching files to track within original path and translation paths.
    # You may want to keep track of only text files like .md or so.
    # These filters are used in original path and in translations path to check which files exist and their corresponding original/translation.
    # Note: files or directories starting with a '.' won't be included as it is a tradition from glob. If you need so, you should explicitly include these in filters.
    # More info about glob patterns: https://docs.python.org/3.6/library/glob.html
    #
    # Not required. Default: '**/*'.
    filters: |-
      **/*.md
      **/*.png

    # Glob patterns matching files to ignore when parsing original files, relative to repo-path.
    # If a translation or original file matches a filter from the above filters, it will still be ignored if matching one of these patterns.
    # More info about glob patterns: https://docs.python.org/3.6/library/glob.html
    #
    # Not required. Default: ''.
    ignores: |-
      **/README.md

  # 2) GENERATION

    # Automatically create stubs for To Create translation files matching one of the given fnmatch patterns, with content defined by stub-template.
    # Checked-out repository must have be able to push to destination branch (defined by gen-branch parameter).
    # More info about fnmatch patterns: https://docs.python.org/3.6/library/fnmatch.html
    #
    # Not required. Default: ''.
    gen-stubs: |-
      *.md

    # The commit message when generating stub files.
    #
    # Not required. Default: ':tada: Created stub translation files'.
    stub-commit: ':tada: Created stub translation files'

    # Template file defining the content of generated stub files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    #
    # This template will be provided a To Create translation track context + special stub arguments.
    #
    # Not required. Default: ''.
    stub-template: '.github/update-tracker/stub-template.md'

    # Automatically copy original files to To Create translation files matching one of the given fnmatch patterns.
    # Checked-out repository must have be able to push to destination branch (defined by gen-branch parameter).
    # More info about fnmatch patterns: https://docs.python.org/3.6/library/fnmatch.html
    #
    # Not required. Default: ''.
    gen-copy: |-
      *.png

    # The commit message when generating file copies.
    #
    # Not required. Default: ':tada: Copied original to translation files'.
    copy-commit: ':tada: Copied original to translation files'

    # The branch where files will be pushed when auto generating changes.
    # If it is not set, files will be committed to the checked-out repository active branch.
    # The actual destination branch, whether it is another branch or the active checked-out branch, must exist and be not branch-protected.
    #
    # Note that if the destination branch is another branch than the active branch, it will always be rebased on the active branch HEAD when the Action triggers and new files are generated.
    # This means you may lose any changes made to this specific branch, you shouldn't use it for other purposes.
    #
    # Not required. Default: ''.
    gen-branch: 'genbranch'

    # 3) INSTRUCTING

    # The GitHub repository where you want to instruct tracked and generated changes, in the form "Author/repo".
    #
    # Not required. Default: '${{ github.repository }}'.
    repository: '${{ github.repository }}'

    # The authorization token to instruct Issues, Projects and Pull requests.
    # You should make sure the GitHub App this token gives access to has enough permissions to update what you set.
    #
    # Also, it is recommended to use your own installation of a GitHub App instead of GitHub Actions provided to strictly define the least permission required.
    # Building GitHub Apps: https://developer.github.com/apps/building-github-apps/
    #
    # Not required. Default: '${{ github.token }}'.
    token: '${{ github.token }}'

    # Request merging gen-branch (if the parameter is set and if changes were applied) to checked-out repository active branch through a Pull Request.
    # The GitHub App token requires read/write access to Pull Requests.
    #
    # Beware: if repository is defined as another repository than the git repo were changes were pushed, requesting merge as Pull Request will fail.
    #
    # Not required. Default: 'false'.
    request-merge: 'true'

    # Instruct translators on translation files matching one of the given fnmatch patterns through GitHub Issues.
    # The GitHub App token requires read/write access to Issues.
    #
    # Not required. Default: ''
    instruct-issues: |-
      *.md

    # The label name to manage issues, issues not labelled with it won't be processed.
    #
    # Not required. Default: 'translation-tracker'.
    issue-label: 'translation-tracker'

    # The issue title template.
    # As the resulting issue title must be unique, the template should include {t.translation.path}.
    # More info about templates in the section below.
    #
    # This template will be provided any translation track context regardless of status + special GitHub arguments.
    #
    # Not required. Default: 'Translation file: {t.translation.path}'.
    issue-title-template: 'Translation file: {t.translation.path}'

    # The issue body template file for To Create translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Initialize translation tracks won't be instructed in Issues.
    #
    # This template will be provided a To Create translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    issue-create-template: .github/update-tracker/issue-create-template.md

    # The issue body template file for To Initialize translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Initialize translation tracks won't be instructed in Issues.
    #
    # This template will be provided a To Initialize translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    issue-initialize-template: .github/update-tracker/issue-init-template.md

    # The issue body template file for To Update translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Update translation tracks won't be instructed in Issues.
    #
    # This template will be provided a To Update translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    issue-update-template: .github/update-tracker/issue-update-template.md

    # The issue body template file for Up-To-Date translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, Up-To-Date translation tracks won't be instructed in Issues.
    #
    # This template will be provided a Up-To-Date translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    issue-uptodate-template: .github/update-tracker/issue-utd-template.md

    # The issue body template file for Orphan translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, Orphan translation tracks won't be instructed in Issues.
    #
    # This template will be provided an Orphan translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    issue-orphan-template: .github/update-tracker/issue-orphan-template.md

    # Instruct translators on translation files matching one of the given fnmatch patterns through GitHub Projects.
    # The Github App token requires read/write access to Projects.
    #
    # Not required. Default: ''.
    instruct-projects: |-
      *.md

    # The project name template.
    # More info about templates in the section below.
    #
    # This template will be provided any translation track context regardless of status + special GitHub arguments.
    #
    # Not required. Default: '{t.translation.language} Update Tracker'.
    project-title-template: '{t.translation.language} Update Tracker'

    # The project description template. Only used when the project is created.
    # More info about templates in the section below.
    #
    # This template will be provided any translation track context regardless of status + special GitHub arguments.
    #
    # Not required. Default: '{t.translation.language} translation effort.'.
    project-description-template: '{t.translation.language} translation effort.'

    # The column template in project to include To Create translation file cards. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Create translation tracks won't be instructed in Projects.
    #
    # This template will be provided a To Create translation track context + special GitHub arguments.
    #
    # Not required. Default: 'To Initialize'.
    project-column-create-template: 'To Initialize'

    # The column template in project to include To Initialize translation file cards. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Initialize translation tracks won't be instructed in Projects.
    #
    # This template will be provided a To Initialize translation track context + special GitHub arguments.
    #
    # Not required. Default: 'To Initialize'.
    project-column-initialize-template: 'To Initialize'

    # The column template in project to include To Update translation file cards. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Update translation tracks won't be instructed in Projects.
    #
    # This template will be provided a To Update translation track context + special GitHub arguments.
    #
    # Not required. Default: 'To Update'.
    project-column-update-template: 'To Update'

    # The column template in project to include Up-To-Date translation file cards. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, Up-To-Date translation tracks won't be instructed in Projects.
    #
    # This template will be provided a Up-To-Date translation track context + special GitHub arguments.
    #
    # Not required. Default: 'Up-To-Date'.
    project-column-uptodate-template: 'Up-To-Date'

    # The column template in project to include Orphan translation file cards. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, Orphan translation tracks won't be instructed in Projects.
    #
    # This template will be provided an Orphan translation track context + special GitHub arguments.
    #
    # Not required. Default: 'Orphans'.
    project-column-orphan-template: 'Orphans'

    # The card template file in project column for To Create translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Create translation tracks won't be instructed in Projects.
    # Also, a note in a card is limited to 1024 characters.
    #
    # This template will be provided a To Create translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    project-card-create-template: .github/update-tracker/card-create-template.md

    # The card template file in project column for To Initialize translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Initialize translation tracks won't be instructed in Projects.
    # Also, a note in a card is limited to 1024 characters.
    #
    # This template will be provided a To Initialize translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    project-card-initialize-template: .github/update-tracker/card-init-template.md

    # The card template file in project column for To Update translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, To Update translation tracks won't be instructed in Projects.
    # Also, a note in a card is limited to 1024 characters.
    #
    # This template will be provided a To Update translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    project-card-update-template: .github/update-tracker/card-update-template.md

    # The card template file in project column for Up-To-Date translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, Up-To-Date translation tracks won't be instructed in Projects.
    # Also, a note in a card is limited to 1024 characters.
    #
    # This template will be provided a Up-To-Date translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    project-card-uptodate-template: .github/update-tracker/card-utd-template.md

    # The card template file in project column for Orphan translation files. This template parameter requires a file path containing the actual template.
    # More info about templates in the section below.
    # If not set, Orphan translation tracks won't be instructed in Projects.
    # Also, a note in a card is limited to 1024 characters.
    #
    # This template will be provided an Orphan translation track context + special GitHub arguments.
    #
    # Not required. Default: ''.
    project-card-orphan-template: .github/update-tracker/card-orphan-template.md
```

You might also find useful these **[examples](#use-case-examples)**.

### About Templates

Templates allow you to define your own custom content when generating stub files or instructing issues and projects.

A template context is given in every template [inputs](#usage): you know for which status the template is going to be formatted, or if it is formatted regardless of the status.
Knowing so, you can create your template using provided arguments.

Arguments must be included in the template as a Python format tag, surrounded with curly brackets, like `{arg}`.

A `t` argument is always given in templates, representing a `TranslationTrack` and holding values described in [`tracks` output](#tracks). Also you can find special arguments in every specific template.
If the argument doesn't exist in a given context, it will result in an error stopping the Action.

Example:
```yml
issue-title-template: "{t.translation.language} translation: {t.translation.path}"
```

This would result in something like `"French translation: wiki/fr/README.md"`.

#### GitHub special arguments

When updating Issues or Projects, special arguments are provided in addition to `t`.

| Argument | Description | **To Create** | **To Initialize** | **To Update** | **Up-To-Date** | **Orphan** |
| --- | --- | --- | --- | --- | --- | --- |
| **`original_url`** | Github URL to original file (using commit rev) | X | X | X | X |  |
| **`raw_original_url`** | Github URL to raw original file (using commit rev) | X | X | X | X |  |
| **`translation_url`** | Github URL to translation file (using branch rev) |  | X | X | X | X |
| **`raw_translation_url`** | Github URL to raw translation file (using commit rev) |  | X | X | X | X |
| **`base_original_url`** | Github URL to base original file (using commit rev) |  |  | X |  |  |
| **`raw_base_original_url`** | Github URL to raw base original file (using commit rev) |  |  | X |  |  |
| **`compare_url`** | Github URL to Github comparison (using base_original and original commit rev) |  |  | X |  |  |

Example for a translation file to update:
```md
Check what changed in `{t.original.path}` [**here**]({compare_url}).
```

Note that these new keys are provided outside of the `t` instance of `TranslationTrack`.

#### Stub special arguments

When generating stub files, a special argument is provided in addition to `t`: **`translation_to_original_path`**. It's the relative path from the translation file parent directory to the original file.

## Outputs

### tracks

JSON representation of tracked translation and original files, as a list of `TranslationTrack`.

A **`TranslationTrack`** object contains:
| Status | Key | Value type | Description |
| --- | --- | --- | --- |
| All | **`translation`** | `TranslationGitFile` object | Tracked translation file. |
| All | **`original`** | `GitFile` object | Matching original file. |
| All | **`status`** | string | Either `"To Create"`, `"To Initialize"`, `"To Update"`, `"Up-To-Date"`, `"Orphan"`. |
| `"To Create"` | **`missing_lines`** | integer | Number of missing lines in translation file, i.e actual number of lines in original file. |
| `"To Initialize"` | **`missing_lines`** | integer | Number of missing lines in translation file, i.e actual number of lines in original file. |
| `"To Update"` | **`base_original`** | `GitFile` object | Base original file used to update most recent translation file. |
| `"To Update"` | **`patch`** | `GitPatch` object | Patch with changes from base original file to original file, instructing required update. |
| `"To Update"` | **`to_rename`** | boolean | Indicates whether the translation file has to be renamed like the new original filename, or not. |
| `"Orphan"` | **`deleted`** | boolean | Indicates whether the original file was deleted, or not (i.e it never existed). |
| `"Orphan"` | **`surplus_lines`** | integer | Number of lines in excess, i.e actual number of lines in translation file. |

Note that some data appears only for a specific status. When requesting a value from this object, say a [template](#about-templates), be sure to understand the context. Should it trigger for every tracks regardless of the status, don't use specific values.

A **`GitFile`** object contains:
| Key | Value type | Description |
| --- | --- | --- |
| **`path`** | string | Path to the file, relative to the git repository. |
| **`filename`** | string | Name of the file. |
| **`directory`** | string | File parent directory, relative to the git repository (might be "."). |
| **`no_trace`** | boolean | Indicates whether the file doesn't exist in git commit history, or it does. |
| **`commit`** | string or null | Sha-1 (40 hexadecimal characters) of the most recent commit modifying the file, null if `no_trace` is true. |
| **`new_file`** | boolean | Indicates whether the file is a new file in commit, or not. |
| **`copied_file`** | boolean | Indicates whether the file was copied in commit, or not. |
| **`renamed_file`** | boolean | Indicates whether the file was renamed in commit, or not. |
| **`rename_from`** | string or null | Path of the old filename if it was renamed. |
| **`rename_to`** | string or null | Path of the new filename if it was renamed. |
| **`deleted_file`** | boolean | Indicates whether the file was deleted in commit, or not. |

A **`TranslationGitFile`** object contains every items of a `GitFile` object, plus:
| Key | Value type | Description |
| --- | --- | --- |
| **`lang_tag`** | string | Language tag, as of RFC5646 |
| **`language`** | string | Language, as of RFC5646 |

A **`GitPatch`** object contains:
| Key | Value type | Description |
| --- | --- | --- |
| **`diff`** | string | Literal git diff indicated what was changed. |
| **`additions`** | integer | Number of lines added. |
| **`deletions`** | integer | Number of lines deleted. |
| **`changes`** | integer | Total number of lines changed. |

Example:
```json
[
    {
        "translation": {
            "path": "wiki/zh/grips-and-tricks.md",
            "no_trace": false,
            "commit": "4ce6ebd661d3a0ce1b0e07212f092e73b5c7c252",
            "new_file": false,
            "copied_file": false,
            "renamed_file": false,
            "rename_from": null,
            "rename_to": null,
            "deleted_file": false,
            "lang_tag": "zh",
            "language": "Chinese"
        },
        "original": {
            "path": "wiki/grips-and-tricks.md",
            "no_trace": false,
            "commit": "d6fb43c9fa56999ce9339bc2bdaa95b7dcbc0964",
            "new_file": false,
            "copied_file": false,
            "renamed_file": false,
            "rename_from": null,
            "rename_to": null,
            "deleted_file": true
        },
        "status": "Orphan",
        "deleted": true,
        "surplus_lines": 0
    }
]
```

You can use this output in other actions in your workflow using [the fromJSON expression](https://help.github.com/en/actions/reference/context-and-expression-syntax-for-github-actions#fromjson).

### open-issues

Comma-separated list containing open issue numbers (when a file requires updating, creation or initialization).

Example: `65,67,70`

## Use-case examples

### Vuepress i18n

Let's imagine a Vuepress tree view as described in [Vuepress site level i18n config](https://vuepress.vuejs.org/guide/i18n.html):

```
docs
├─ README.md
├─ foo.md
├─ nested
│  └─ README.md
└─ zh
│  ├─ README.md
│  ├─ foo.md
│  └─ nested
│     └─ README.md
└─ fr
   ├─ README.md
   ├─ foo.md
   └─ nested
      └─ README.md
```

**Original pages** are located in **`docs`**, while **translation pages** are reflected in **`docs/zh`** and **`docs/fr`**.

To keep track of discrepancies between original pages in `docs` and translation pages in `docs/zh` and `docs/fr`, see the [example workflow file](examples/vuepress-update-tracker.yml) using this action.

## API reference

Documentation can be found in Python modules within [`src/`](src).

## License

This project assets (source code, documentation and examples) are published under the [MIT License](LICENSE).
