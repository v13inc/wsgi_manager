#!/bin/bash
#
# switch_app_version <commit hash>
# - moves current src/ directory to src_<date>
# - extracts archive and moves it to src directory
# - restarts app with minimal downtime
#

commit=$1

if [ -e /home/app/src ]; then
  rm /home/app/src
fi
ln -s /home/app/src_$commit /home/app/src

sudo supervisorctl restart {{ app.name }}
