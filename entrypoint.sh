#!/bin/bash

# 1: repo local path
# 2: original files path
# 3: ignored files paths
# 4: translation files tags and paths
# 5: file suffix
# 6: Github repo
# 7: bot label
# 8: token
# 9: log level (DEBUG, INFO, WARNING or CRITICAL)
# 10: auto create (true, false)
# 11: update issues (true, false)
# 12: update projects (true, false)
result=$(python /usr/src/app/wiki-update.py $1 $2 $3 $4 $5 $6 $7 $8 $9 ${10} ${11} ${12})
if [ "$result" = "1" ]; then
    echo "Script failed"
    exit 1
fi
