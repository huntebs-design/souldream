#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
stage_dir="$(mktemp -d /private/tmp/dilse-web-release.XXXXXX)"

cleanup() {
    rm -r "${stage_dir}"
}
trap cleanup EXIT

cd "${project_dir}"

cp \
    Dockerfile \
    requirements.txt \
    web.py \
    app.py \
    main.py \
    seo_content.py \
    seo_expansion.py \
    "${stage_dir}/"

cp -R \
    .streamlit \
    assets \
    public \
    downloads \
    components \
    "${stage_dir}/"

railway up "${stage_dir}" \
    --path-as-root \
    --project 09936927-e510-49e8-b0c3-96a138a97b66 \
    --environment production \
    --service dilse-web \
    --detach \
    --message "Publish DilSe web runtime and signed Android APK"
