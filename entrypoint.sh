#!/bin/sh -l

# 1: repo local path
# 2: original pages path
# 3: ignored files paths
# 4: translation pages paths
# 5: file suffix
# 6: Github repo
# 7: bot label
# 8: token
# 9: log level (DEBUG, INFO, WARNING or CRITICAL)
if [ python /usr/src/app/wiki-update.py $1 $2 $3 $4 $5 $6 $7 $8 $9 = 0 ]; then
    echo "Script failed"
    exit 1
fi

echo "::set-output name=translation-status::${translation-status}"
echo "::set-output name=open-issues::${open-issues}"
