from updater import UpdaterTemplate

# Stub files templates
STUB_COMMIT_MSG = ":tada: Creating stub translation pages"
STUB_FILE_CONTENT = UpdaterTemplate('---\n'
'translation-done: false\n'
'---\n'
'::: danger\n'
'Sorry, this page has not been translated yet, you can either:\n'
'- refer to the [original English version](<{t.translation_to_original_path}>),\n'
'- wait for a translation to be done,\n'
'- or contribute to translation effort [here](https://github.com/bsmg/wiki).\n'
':::\n'
'\n'
'_Note for translators: this page was generated automatically, please remove this content before starting translation_\n'
)

# Issue body message format and title
ISSUE_TITLE = UpdaterTemplate("Translation page: {t.translation_path}")
ISSUE_BODY_UPDATE = UpdaterTemplate(
    '## :bookmark_tabs: Translation update\n'
    'Since **`{t.translation_path}`** was last updated, changes have been detected in the original wiki page `{t.original_path}` it is based on.\n'
    '\n'
    'Please update **[the translation here](<{t.translation_url}>)** accordingly, respecting contribution guidelines.\n'
    '\n'
    '### :bar_chart: Workload\n'
    '\n'
    'Calculated changes made to the original file `{t.original_path}` (as lines):\n'
    '\n'
    '```diff\n'
    '+ {t.patch_additions} additions\n'
    '- {t.patch_deletions} deletions\n'
    '! {t.patch_changes} total lines updated\n'
    '```\n'
    '\n'
    '### :wrench: Translation tools\n'
    '\n'
    'You can choose one of the following options to help you see what changed:\n'
    '1. Use this [Github comparison](<{t.compare_url}>) and find the comparison on the file **`{t.original_path}`**.\n'
    '2. OR use [Diffchecker web version](https://www.diffchecker.com/). Copy/paste [this original text](<{t.raw_base_original_url}>) in the left field and [this changed text](<{t.raw_original_url}>) in the right field, then press "Find Difference".\n'
    '3. OR simply use the detailed patch below.\n'
    '\n'
    'Detailed additions and deletions on `{t.original_path}`:\n'
    '```diff\n'
    '{t.patch_diff}\n'
    '```\n'
)
ISSUE_BODY_TBI = UpdaterTemplate(
    '## :page_facing_up: Translation initialization\n'
    'A new original wiki page has been detected: `{t.original_path}`. It has no associated translation yet (though the file `{t.translation_path}` already exists).\n'
    '\n'
    'Please **[initialize the translation here](<{t.translation_url}>)**. Base your translation on the [original English version](<{t.original_url}>).\n'
    '\n'
    '### :bar_chart: Workload\n'
    '\n'
    'Calculated lines to translate from the original file `{t.original_path}`:\n'
    '\n'
    '```diff\n'
    '+ {t.patch_additions} lines\n'
    '```\n'
)
ISSUE_BODY_TBC = UpdaterTemplate(
    '## :page_facing_up: Translation creation & initialization\n'
    'A new original wiki page has been detected: `{t.original_path}`. It has no associated translation yet.\n'
    '\n'
    'Please create the file **{t.translation_path}** and initialize the translation based on the [original English version](<{t.original_url}>).\n'
    '\n'
    '### :bar_chart: Workload\n'
    '\n'
    'Calculated lines to translate from the original file `{t.original_path}`:\n'
    '\n'
    '```diff\n'
    '+ {t.patch_additions} lines\n'
    '```\n'
)
ISSUE_BODY_UTD = UpdaterTemplate(
    '## :heavy_check_mark: Nothing to do\n'
    'Thanks to your involvement, `{t.translation_path}` is up-to-date! :1st_place_medal:\n'
    '\n'
    'Let\'s keep it that way for every wiki pages!\n'
)

# Project card messages and title (cards limited to 1024 chars)
PROJECT_TITLE = UpdaterTemplate("Wiki {t.language} Update Tracker")
PROJECT_DESCRIPTION = UpdaterTemplate("{t.language} translation effort.")
PROJECT_COLUMN_TBC = UpdaterTemplate("To Initialize")
PROJECT_COLUMN_TBI = PROJECT_COLUMN_TBC
PROJECT_COLUMN_UPDATE = UpdaterTemplate("To Update")
PROJECT_COLUMN_UTD = UpdaterTemplate("Up-To-Date")

PROJECT_CARD_UPDATE = UpdaterTemplate(
    '**Update [`{t.translation_path}`](<{t.translation_url}>)** using:\n'
    '* **[Github comparison](<{t.compare_url}>)**\n'
    '  * Comparison on **`{t.original_path}`**\n'
    '* or **[Diffchecker web](https://www.diffchecker.com)**\n'
    '  * [Old original content](<{t.raw_base_original_url}>)\n'
    '  * [Recent original content](<{t.raw_original_url}>)\n'
    '\n'
    '**`{t.original_path}`** changes:\n'
    '```diff\n'
    '+ {t.patch_additions} lines\n'
    '- {t.patch_deletions} lines\n'
    '```\n'
)
PROJECT_CARD_TBI = UpdaterTemplate(
    '**Initialize [`{t.translation_path}`](<{t.translation_url}>)** using:\n'
    '* **[The original file](<{t.original_url}>)**\n'
    '  * Use *Raw* for better accuracy\n'
    '\n'
    '**`{t.original_path}`** contains:\n'
    '```diff\n'
    '+ {t.patch_additions} lines\n'
    '```\n'
)
PROJECT_CARD_TBC = UpdaterTemplate(
    '**Create and initialize `{t.translation_path}`** using:\n'
    '* **[The original file](<{t.original_url}>)**\n'
    '  * Use *Raw* for better accuracy\n'
    '\n'
    '**`{t.original_path}`** contains:\n'
    '```diff\n'
    '+ {t.patch_additions} lines\n'
    '```\n'
)
PROJECT_CARD_UTD = UpdaterTemplate(
    ':heavy_check_mark: **`{t.translation_path}`** is up-to-date!\n'
)
