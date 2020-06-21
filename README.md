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

- New input `auto-copy` in addition to `auto-create`.
- New input `auto-branch` to 
- **WARNING**: input `ignored-paths` was removed, replaced by `exclude`
- **WARNING**: input `file-suffix` was removed, no replacement 
- **WARNING**: input `update-issues` was removed, replaced by `globs`
- **WARNING**: input `auto-create` was removed, replaced by `auto-create-globs` accepting glob patterns instead of simply enabling/disabling
- **WARNING**: input `bot-label` was renamed to `issue-label`

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

Then use this job in your workflow file (you might find useful these [examples](#use-case-examples)):

```yml
- uses: Awagi/wiki-update-tracker@v1.8
  with:
    #
    #
    repo-path: ''

    #
    #
    original-path: ''

    #
    #
    ignored-paths: ''

    #
    #
    translations: ''

    #
    #
    repository: ''

    #
    #
    file-suffix: ''

    #
    #

```

**`repo-path`**

The path where the git repo is located within the filesystem.

Example: `${GITHUB_WORKSPACE}`

**`original-path`**

The original pages path. It can be a file or a directory.

If a translation path given in `translations` is part of the `original-path` subdirectories, it will only be treated as translation files.

It must be given relatively to the git repo root path.

Example: `wiki`

**`ignored-paths`**

A blacklist to mark unassociated directories and files within the original pages path.

These must be given relatively to the git repo root path.

Example: `wiki/LICENSE,wiki/.vuepress`

**`translations`**

The translation pages relative paths and their associated language tag. You may have different paths for translation, but each must follow the same structure as the original pages path.

These must be given relatively to the git repo root path. Language tags are defined in [RFC 5646](https://tools.ietf.org/html/rfc5646).

**`repository`**

The GitHub repository in the form `Author/repo`, used to update issues. Defaults to `${{ github.repository }}`.

**`file-suffix`**

The file suffix (or extension) used to identify Wiki page. Defaults to `.md`.

**`token`**

The job's access token, given with `${{ secrets.GITHUB_TOKEN }}` or other means to restrict to least-privilege permissions (recommended).

[More info](https://help.github.com/en/actions/configuring-and-managing-workflows/authenticating-with-the-github_token).

**`log-level`**

The Python script's log level. It can be `DEBUG`, `INFO`, `WARNING` or `CRITICAL`. Defaults to `INFO`.

[More info](https://docs.python.org/3/library/logging.html).

**`auto-create`**

Automatically create stub files for non-existent translation files matching given patterns. Includes a templated content containing the `translation-done: false` header, for To Be Initialized status.

The Action will commit through git and push to Github repo on the branch `auto-branch`. As such, checked-out repository must have read/write access to Contents.

The value is a comma-separated list of [glob patterns](https://en.wikipedia.org/wiki/Glob_%28programming%29).

**`auto-copy`**

Automatically copy original files into non-existent corresponding translation file matching given patterns.

Copied files won't be considered for translation, use this for static files that don't require translation.

This function occurs after `auto-create`, so "To Create" translation files matching both create and copy globs pattern will only be created, not copied.

The Action will commit through git and push to Github repo on the branch `auto-branch`. As such, checked-out repository must have read/write access to Contents.

The value is a comma-separated list of [glob patterns](https://en.wikipedia.org/wiki/Glob_%28programming%29).

**`auto-branch`**

**`request-merge`**

Enable with "1" or "true".

**`update-issues-glob`**

Enable Github Issues update.
It can be `true`, `1`, `yes` to enable issues update or `false`, `0`, `no` to disable issues update.

The 

**`issue-label`**

The Github label used to track managed issues. Issues with this label will be seen by the script, other will be out of scope.

Required when `update-issues` is enabled.

[More info](https://help.github.com/en/github/managing-your-work-on-github/about-labels).

**`issue-title-template`**

The issue title [template](#about-templates).

As the resulting issue title is used as an identifier for a particular translation file, it must be unique. So your template must contain `{t.translation_path}`.

**`issue-create-template`**

The issue body [template](#about-templates) for "To Create" translation files.

**`issue-initialize-template`**

The issue body [template](#about-templates) for "To Initialize" translation files.

**`issue-update-template`**

The issue body [template](#about-templates) for "To Update" translation files.

**`issue-uptodate-template`**

The issue body [template](#about-templates) for "Up-To-Date" translation files.

**`issue-orphan-template`**

The issue body [template](#about-templates) for "Orphan" translation files.

**`update-projects-glob`**


Enable Github Projects update. When a project isn't found, it is created.

It can be `true`, `1`, `yes` to enable projects update or `false`, `0`, `no` to disable projects update.

**`project-title-template`**

The project name [template](#about-templates).

You can easily filter your projects with this template. For example, the default template creates a project for every languages.

**`project-description-template`**

The project description [template](#about-templates).

The resulting description is only set to a project it is created, the Action does not update it.

**`project-column-create-template`**

The column name [template](#about-templates) in project to include "To Create" translation file cards.

You can easily filter your columns with these templates.
For example setting the same column name for `project-column-create-template` and `project-column-initialize-template` will make only one column and put all "To Create" and "To Initialize" translation file cards in it.

**`project-column-initialize-template`**

The column [template](#about-templates) in project to include "To Initialize" translation file cards.

**`project-column-update-template`**

The column [template](#about-templates) in project to include "To Update" translation file cards.

**`project-column-uptodate-template`**

The column [template](#about-templates) in project to include "Up-To-Date" translation file cards.

**`project-column-orphan-template`**

The column [template](#about-templates) in project to include "Orphan" translation file cards.

**`project-card-create-template`**

The card [template](#about-templates) in project column for "To Create" translation files.

The resulting card content must be unique, keep `{t.translation_path}` in the template.

These cards will be put in `project-column-create-template` column.

**`project-card-initialize-template`**

The card [template](#about-templates) in project column for "To Initialize" translation files.

The resulting card content must be unique, keep `{t.translation_path}` in the template.

These cards will be put in `project-column-initiliaze-template` column.

**`project-card-update-template`**

The card [template](#about-templates) in project column for "To Update" translation files.

The resulting card content must be unique, keep `{t.translation_path}` in the template.

**`project-card-uptodate-template`**

The card [template](#about-templates) in project column for "Up-To-Date" translation files.

The resulting card content must be unique, keep `{t.translation_path}` in the template.

**`project-card-orphan-template`**

The card [template](#about-templates) in project column for "Orphan" translation files.

The resulting card content must be unique, keep `{t.translation_path}` in the template.

### About Templates

Templates allow you to define your own custom content for stub files, issues and projects.

According to tracked translation files, different contexts are given to a template to format the resulting content.
This means some keys are given only in a particular status.

#### Template keys

Below are the keys you can find and use in your template for each status and when no status is specified.

| | | Any status | **To Create** | **To Initialize** | **To Update** | **Up-To-Date** | **Orphan** |
|-|-|-|-|-|-|-|-|
| `language` | Language name | X | X | X | X | X | X |
| `lang_tag` | Language tag as of RFC 5646 | X | X | X | X | X | X |
| `status` | Translation file status | X | X | X | X | X | X |
| `translation_filename` | Translation file name | X | X | X | X | X | X |
| `original_filename` | Original file name | X | X | X | X | X | X |
| `base_original_filename` | Base original file* name | X | X | X | X | X | X |
| `translation_path` | Path of the translation file | X | X | X | X | X | X |
| `original_path` | Path of the original file | X | X | X | X | X | X |
| `original_commit` | Original file commit sha | X | X | X | X | X |  |
| `translation_commit`| Translation file commit sha |  |  | X | X | X | X |
| `patch_diff` | String comparison |  |  |  | X |  |  |
| `patch_additions` | Number of lines to add | X | X | X | X | X | X |
| `patch_deletions` | Number of lines to delete | X | X | X | X | X | X |
| `patch_changes` | Number of lines changed |  |  |  | X |  |  |
| `translation_to_original_path` | Relative path from translation file parent directory to original file | X | X | X | X | X | X |

_*The base original file is the latest original file used to translate the current translation file: it differs from original file in "To Update" context and is the same in "Up-To-Date"_

#### Github template keys

When updating Issues or Projects, some keys are provided in addition to those described above.

| | | Any status | **To Create** | **To Initialize** | **To Update** | **Up-To-Date** | **Orphan** |
|-|-|-|-|-|-|-|-|
| `translation_url` | Github URL to translation file (using branch rev) | X | X | X | X | X | X |
| `original_url` | Github URL to original file (using commit rev) | X | X | X | X | X |  |
| `raw_original_url` | Github URL to raw original file (using commit rev) |  | X | X | X | X |  |
| `raw_translation_url` | Github URL to raw translation file (using commit rev) |  |  | X | X | X | X |
| `base_original_url` | Github URL to base original file (using commit rev) |  |  |  | X |  |  |
| `raw_base_original_url` | Github URL to raw base original file (using commit rev) |  |  |  | X |  |  |
| `compare_url` | Github URL to Github comparison (using base_original and original commit rev) |  |  |  | X |  |  |

#### Template key usage

Keys must be included in the template like a Python format string including a `t` object holding above-described attributes. If the key doesn't exist in a specific context, it will result in an error stopping the Action.

Example:
```yml
issue-title-template: "{t.language} translation: {t.translation_path}"
```

This would result in something like `"French translation: wiki/fr/README.md"`.

**Note**: even though some keys are provided in some contexts, it doesn't mean they are always relevant.

## Outputs

### tracks

JSON representation of tracked translation and original files, as a list of `TranslationTrack`.

A **`TranslationTrack`** object contains:
| Key | Value type | Description |
| --- | --- | --- |
| **`translation`** | `TranslationGitFile` object | Tracked translation file. |
| **`original`** | `GitFile` object | Matching original file. |
| **`status`** | string | Either `"To Create"`, `"To Initialize"`, `"To Update"`, `"Up-To-Date"`, `"Orphan"`. |

Additional data may be provided according to a track status:
| Status | Key | Value type | Description |
| `"To Create"` | **`missing_lines`** | integer | Number of missing lines in translation file, i.e actual number of lines in original file. |
| `"To Initialize"` | **`missing_lines`** | integer | Number of missing lines in translation file, i.e actual number of lines in original file. |
| `"To Update"` | **`base_original`** | `GitFile` object | Base original file used to update most recent translation file. |
| `"To Update"` | **`patch`** | `GitPatch` object | Patch with changes from base original file to original file, instructing required update. |
| `"To Update"` | **`to_rename`** | boolean | Indicates whether the translation file has to be renamed like the new original filename, or not. |
| `"Orphan"` | **`deleted`** | boolean | Indicates whether the original file was deleted, or not (i.e it never existed). |
| `"Orphan"` | **`surplus_lines`** | integer | Number of lines in excess, i.e actual number of lines in translation file. |

A **`GitFile`** object contains:
| Key | Value type | Description |
| **`path`** | string | Path to the file, relative to the git repository. |
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
| **`lang_tag`** |  |  |
| **`language`** |  |  |



**`TranslationTrack`** values
| Type | JSON Type


You can [use this output in your workflow](https://help.github.com/en/actions/reference/context-and-expression-syntax-for-github-actions#fromjson) like so: ``

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

**`open-issues`**

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
