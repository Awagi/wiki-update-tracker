# Issue body message format and title
ISSUE_TITLE = "Translation page: {t.translation_path}"
ISSUE_BODY_UPDATE = (
    '## :bookmark_tabs: Translation update\n'
    'Since **`{t.translation.path}`** was last updated, changes have been detected in the original wiki page `{t.original.path}` it is based on.\n'
    '\n'
    'Please update **[the translation here]({tr_url})** accordingly, respecting contribution guidelines.\n'
    '\n'
    '### :bar_chart: Workload\n'
    '\n'
    'Calculated changes made to the original file `{t.original.path}` (as lines):\n'
    '\n'
    '```diff\n'
    '+ {t.patch.additions} additions\n'
    '- {t.patch.deletions} deletions\n'
    '! {t.patch.changes} total lines updated\n'
    '```\n'
    '\n'
    '### :wrench: Translation tools\n'
    '\n'
    'You can choose one of the following options to help you see what changed:\n'
    '1. Use this [Github comparison]({compare_url}) and find the comparison on the file **`{t.original.path}`**.\n'
    '2. OR use [Diffchecker web version](https://www.diffchecker.com/). Copy/paste [this original text]({oldori_raw_url}) in the left field and [this changed text]({ori_raw_url}) in the right field, then press "Find Difference".\n'
    '3. OR simply use the detailed patch below.\n'
    '\n'
    'Detailed additions and deletions on `{t.original.path}`:\n'
    '```diff\n'
    '{t.patch.diff}\n'
    '```\n'
)
ISSUE_BODY_TBI = (
    '## :page_facing_up: Translation initialization\n'
    'A new original wiki page has been detected: `{t.original.path}`. It has no associated translation yet (though the file `{t.translation.path}` already exists).\n'
    '\n'
    'Please **[initialize the translation here]({tr_url})**. Base your translation on the [original English version]({or_url}).\n'
)
ISSUE_BODY_TBC = (
    '## :page_facing_up: Translation creation & initialization\n'
    'A new original wiki page has been detected: `{t.original.path}`. It has no associated translation yet.\n'
    '\n'
    'Please create the file **{t.translation.path}** and initialize the translation based on the [original English version]({or_url}).\n'
)
ISSUE_BODY_UTD = (
    '## :heavy_check_mark: Nothing to do\n'
    'Thanks to your involvement, `{t.translation.path}` is up-to-date! :1st_place_medal:\n'
    '\n'
    'Let\'s keep it that way for every wiki pages!\n'
)

# Project card messages and title (cards limited to 1024 chars)
PROJECT_TITLE = "Wiki {language} Update Tracker"
PROJECT_DESCRIPTION = "{language} translation effort."
PROJECT_COLUMN_TBC = "To Initialize"
PROJECT_COLUMN_TBI = "To Initialize"
PROJECT_COLUMN_UPDATE = "To Update"
PROJECT_COLUMN_UTD = "Up-To-Date"

PROJECT_CARD_UPDATE = (
    '**Update [`wiki/fr/about/supports.md`]({tr_url})** using:\n'
    '* **[Github comparison]({compare_url})**\n'
    '  * Comparison on **`wiki/about/supports.md`**\n'
    '* or **[Diffchecker web](https://www.diffchecker.com)**\n'
    '  * [Old original content]({oldori_raw_url})\n'
    '  * [Recent original content]({ori_raw_url})\n'
    '\n'
    '**`wiki/about/supports.md`** changes:\n'
    '```diff\n'
    '    + {t.patch.additions} lines\n'
    '    - {t.patch.deletions} lines\n'
    '```\n'
)
PROJECT_CARD_TBI = (
    '**Initialize [`{t.translation.path}`]({tr_url})** using:\n'
    '* **[The original file]({or_url})**\n'
    '  * Use *Raw* for better accuracy\n'
    '\n'
    '**`{t.original.path}`** contains:\n'
    '```diff\n'
    '+ {t.patch.additions} lines\n'
    '```\n'
)
PROJECT_CARD_TBC = (
    '**Create and initialize `{t.translation.path}`** using:\n'
    '* **[The original file]({or_url})**\n'
    '  * Use *Raw* for better accuracy\n'
    '\n'
    '**`{t.original.path}`** contains:\n'
    '```diff\n'
    '+ {t.patch.additions} lines\n'
    '```\n'
)
PROJECT_CARD_UTD = (
    ':heavy_check_mark: **`{t.translation.path}`** is up-to-date!\n'
)
