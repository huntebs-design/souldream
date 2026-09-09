#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
mobile_dir="${project_dir}/mobile"
downloads_dir="${project_dir}/downloads"
flutter_bin="${FLUTTER_BIN:-flutter}"
android_env="${project_dir}/.env.android"

if [[ -f "${android_env}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${android_env}"
    set +a
fi

if [[ ! -f "${mobile_dir}/android/key.properties" ]]; then
    printf 'Release signing is missing. Run scripts/create_android_signing_key.sh first.\n' >&2
    exit 1
fi

if ! command -v "${flutter_bin}" >/dev/null 2>&1 && [[ ! -x "${flutter_bin}" ]]; then
    printf 'Flutter was not found. Set FLUTTER_BIN to the Flutter executable.\n' >&2
    exit 1
fi

build_args=(
    build apk
    --release
    --dart-define="DILSE_API_URL=${DILSE_API_URL:-https://www.baatdilse.com/api}"
)

for variable_name in \
    FIREBASE_API_KEY \
    FIREBASE_APP_ID \
    FIREBASE_MESSAGING_SENDER_ID \
    FIREBASE_PROJECT_ID; do
    variable_value="${!variable_name:-}"
    if [[ -z "${variable_value}" ]]; then
        printf 'Required Android notification setting is missing: %s\n' "${variable_name}" >&2
        exit 1
    fi
    build_args+=(--dart-define="${variable_name}=${variable_value}")
done

cd "${mobile_dir}"
"${flutter_bin}" pub get
"${flutter_bin}" test
"${flutter_bin}" "${build_args[@]}"

mkdir -p "${downloads_dir}"
cp "${mobile_dir}/build/app/outputs/flutter-apk/app-release.apk" \
    "${downloads_dir}/DilSe-latest.apk"
(
    cd "${downloads_dir}"
    shasum -a 256 DilSe-latest.apk > DilSe-latest.apk.sha256
)

printf 'Signed APK: %s\n' "${downloads_dir}/DilSe-latest.apk"
printf 'Checksum: %s\n' "${downloads_dir}/DilSe-latest.apk.sha256"
