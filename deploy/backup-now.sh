#!/bin/sh
# Backup on demand, without waiting for the night.
. "$(dirname -- "$0")/lib.sh"

dc exec -T backup backup.sh
