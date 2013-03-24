#!/bin/bash
. /home/app/env/bin/activate 
cd /home/app/src_$1
({{ app.bootstrap }}) && touch /home/app/.bootstrapped

