#!/usr/bin/env bash

set -euo pipefail
umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
backup_dir="${project_dir}/backups/railway"
ssh_key="${project_dir}/.railway/dilse_backup_ed25519"
volume_id="bcdf0198-d8da-4c2c-8050-793581a62e53"
remote_snapshot="/dilse-weekly-backup.db"
backup_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
final_path="${backup_dir}/dilse-${backup_stamp}.db"
partial_path="${final_path}.partial"

cleanup() {
    if [[ -n "${SSH_AGENT_PID:-}" ]]; then
        ssh-agent -k >/dev/null 2>&1 || true
    fi
    rm -f "${partial_path}"
}
trap cleanup EXIT

if [[ ! -f "${ssh_key}" ]]; then
    printf 'Backup key is missing: %s\n' "${ssh_key}" >&2
    exit 1
fi

mkdir -p "${backup_dir}"
eval "$(ssh-agent -s)" >/dev/null
ssh-add "${ssh_key}" >/dev/null

cd "${project_dir}"

snapshot_program='import os, sqlite3; source = sqlite3.connect(os.environ["DATABASE_PATH"], timeout=30); target = sqlite3.connect("/data/dilse-weekly-backup.db", timeout=30); source.backup(target); result = target.execute("PRAGMA quick_check").fetchone()[0]; target.close(); source.close(); assert result == "ok", result'
railway ssh --service dilse-api "python -c '${snapshot_program}'"

railway volume files --volume "${volume_id}" download \
    "${remote_snapshot}" "${partial_path}" --overwrite --json >/dev/null

integrity_result="$(sqlite3 "${partial_path}" 'PRAGMA quick_check;')"
if [[ "${integrity_result}" != "ok" ]]; then
    printf 'Downloaded backup failed SQLite integrity validation: %s\n' "${integrity_result}" >&2
    exit 1
fi

mv "${partial_path}" "${final_path}"
shasum -a 256 "${final_path}" > "${final_path}.sha256"

printf 'Backup created: %s\n' "${final_path}"
printf 'Integrity: ok\n'
