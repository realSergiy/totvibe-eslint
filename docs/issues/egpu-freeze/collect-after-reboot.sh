#!/usr/bin/env bash
set -euo pipefail

if (( EUID != 0 )); then
  echo "Run this script as root." >&2
  exit 1
fi

capture_root=/var/log/egpu-freeze
run_dir=$(find "$capture_root" -mindepth 1 -maxdepth 1 -type d -name 'run-*' -printf '%p\n' | sort | tail -n 1)
if [[ -z "$run_dir" ]]; then
  echo "No capture run found under $capture_root." >&2
  exit 1
fi

journalctl -b -1 -o short-precise --no-pager > "$run_dir/previous-boot-journal.log"
journalctl -b -1 -k -o short-precise --no-pager > "$run_dir/previous-boot-kernel.log"
find /sys/fs/pstore -maxdepth 1 -type f -exec cp --preserve=timestamps '{}' "$run_dir/" ';'
find /var/crash -maxdepth 2 -type f -printf '%p %s bytes %TY-%Tm-%TdT%TH:%TM:%TS\n' > "$run_dir/crash-files.txt"
chgrp -R adm "$run_dir"
chmod -R g+rX "$run_dir"
sync
echo "Recovery evidence saved in $run_dir"
