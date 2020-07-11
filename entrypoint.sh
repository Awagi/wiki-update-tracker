#!/bin/bash

OUTPUT_NAME="transation-tracks"

cmd="python /usr/src/app/main.py"

arg_loglevel=$1  # 1) log-level
arg_repopath=$2  # 2) repo-path
arg_original=$3  # 3) original
arg_translations=$4  # 4) translations, \n separated
arg_filters=$5  # 5) filters, \n separated
arg_ignores=$6  # 6) ignores, \n separated
arg_genstubs=$7  # 7) gen-stubs, \n separated
arg_stubcommit=$8  # 8) stub-commit
arg_stubtemplate=$9  # 9) stub-template
arg_gencopy=${10}  # 10) gen-copy, \n separated
arg_copycommit=${11}  # 11) copy-commit
arg_genbranch=${12}  # 12) gen-branch
arg_repository=${13}  # 13) repository
arg_token=${14}  # 14) token
arg_requestmerge=${15}  # 15) request-merge
arg_instructissues=${16}  # 16) instruct-issues, \n separated
arg_issuelabel=${17}  # 17) issue-label
arg_issuetitletemplate=${18}  # 18) issue-title-template
arg_issuecreatetemplate=${19}  # 19) issue-create-template
arg_issueinitializetemplate=${20}  # 20) issue-initialize-template
arg_issueupdatetemplate=${21}  # 21) issue-update-template
arg_issueuptodatetemplate=${22}  # 22) issue-uptodate-template
arg_issueorphantemplate=${23}  # 23) issue-orphan-template
arg_instructprojects=${24}  # 24) instruct-projects, \n separated
arg_projecttitletemplate=${25}  # 25) project-title-template
arg_projectdescriptiontemplate=${26}  # 26) project-description-template
arg_projectcolumncreatetemplate=${27}  # 27) project-column-create-template
arg_projectcolumninitializetemplate=${28}  # 28) project-column-initialize-template
arg_projectcolumnupdatetemplate=${29}  # 29) project-column-update-template
arg_projectcolumnuptodatetemplate=${30}  # 30) project-column-uptodate-template
arg_projectcolumnorphantemplate=${31}  # 31) project-column-orphan-template
arg_projectcardcreatetemplate=${32}  # 32) project-card-create-template
arg_projectcardinitializetemplate=${33}  # 33) project-card-initialize-template
arg_projectcardupdatetemplate=${34}  # 34) project-card-update-template
arg_projectcarduptodatetemplate=${35}  # 35) project-card-uptodate-template
arg_projectcardorphantemplate=${36}  # 36) project-card-orphan-template

# build arguments for script
# set optional arguments
[ -n "$arg_loglevel" ] && args="$args -l $arg_loglevel"
[ -n "$arg_repopath" ] && args="$args -r \"$arg_repopath\""
[ -n "$arg_filters" ] && args="$args --filter ${arg_filters//$'\n'/ }"
[ -n "$arg_ignores" ] && args="$args --ignore ${arg_ignores//$'\n'/ }"
[ -n "$arg_genstubs" ] && args="$args --gen-stubs ${arg_genstubs//$'\n'/ }"
[ -n "$arg_stubcommit" ] && args="$args --stub-commit \"$arg_stubcommit\""
[ -n "$arg_stubtemplate" ] && args="$args --stub-template \"$arg_stubtemplate\""
[ -n "$arg_gencopy" ] && args="$args --gen-copy ${arg_gencopy//$'\n'/ }"
[ -n "$arg_copycommit" ] && args="$args --copy-commit \"$arg_copycommit\""
[ -n "$arg_genbranch" ] && args="$args --gen-branch \"$arg_genbranch\""
[ -n "$arg_repository" ] && [ -n "$arg_token" ] && args="$args --github \"$arg_repository\" \"$arg_token\""
if [ "$arg_requestmerge" == "true" ] || [ "$arg_requestmerge" == "1" ]; then
    args="$args --request-merge"  # request-merge
fi
[ -n "$arg_instructissues" ] && args="$args --instruct-issues ${arg_instructissues//$'\n'/ }"
[ -n "$arg_issuelabel" ] && args="$args --issue-label \"$arg_issuelabel\""
[ -n "$arg_issuetitletemplate" ] && args="$args --issue-title-template \"$arg_issuetitletemplate\""
[ -n "$arg_issuecreatetemplate" ] && args="$args --issue-create-template \"$arg_issuecreatetemplate\""
[ -n "$arg_issueinitializetemplate" ] && args="$args --issue-initialize-template \"$arg_issueinitializetemplate\""
[ -n "$arg_issueupdatetemplate" ] && args="$args --issue-update-template \"$arg_issueupdatetemplate\""
[ -n "$arg_issueuptodatetemplate" ] && args="$args --issue-uptodate-template \"$arg_issueuptodatetemplate\""
[ -n "$arg_issueorphantemplate" ] && args="$args --issue-orphan-template \"$arg_issueorphantemplate\""
[ -n "$arg_instructprojects" ] && args="$args --instruct-projects \"${arg_instructprojects//$'\n'/ }\""
[ -n "$arg_projecttitletemplate" ] && args="$args --project-title-template \"$arg_projecttitletemplate\""
[ -n "$arg_projectdescriptiontemplate" ] && args="$args --project-description-template \"$arg_projectdescriptiontemplate\""
[ -n "$arg_projectcolumncreatetemplate" ] && args="$args --project-column-create-template \"$arg_projectcolumncreatetemplate\""
[ -n "$arg_projectcolumninitializetemplate" ] && args="$args --project-column-initialize-template \"$arg_projectcolumninitializetemplate\""
[ -n "$arg_projectcolumnupdatetemplate" ] && args="$args --project-column-update-template \"$arg_projectcolumnupdatetemplate\""
[ -n "$arg_projectcolumnuptodatetemplate" ] && args="$args --project-column-uptodate-template \"$arg_projectcolumnuptodatetemplate\""
[ -n "$arg_projectcolumnorphantemplate" ] && args="$args --project-column-orphan-template \"$arg_projectcolumnorphantemplate\""
[ -n "$arg_projectcardcreatetemplate" ] && args="$args --project-card-create-template \"$arg_projectcardcreatetemplate\""
[ -n "$arg_projectcardinitializetemplate" ] && args="$args --project-card-initialize-template \"$arg_projectcardinitializetemplate\""
[ -n "$arg_projectcardupdatetemplate" ] && args="$args --project-card-update-template \"$arg_projectcardupdatetemplate\""
[ -n "$arg_projectcarduptodatetemplate" ] && args="$args --project-card-uptodate-template \"$arg_projectcarduptodatetemplate\""
[ -n "$arg_projectcardorphantemplate" ] && args="$args --project-card-orphan-template \"$arg_projectcardorphantemplate\""

# set positional arguments
args="$args \"$arg_original\""
args="$args ${arg_translations//$'\n'/ }"

cmdargs="$cmd$args"

echo $cmdargs

result=$(sh -c "$cmdargs")

if [ $? != 0 ]; then
    echo "::error:: Script failure, check logs"
    exit 1
fi

echo "::set-output name=${OUTPUT_NAME}::${result}"
