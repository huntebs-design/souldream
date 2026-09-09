#!/usr/bin/env bash

set -euo pipefail
umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
android_dir="${project_dir}/mobile/android"
keystore_path="${android_dir}/dilse-release.jks"
properties_path="${android_dir}/key.properties"
key_alias="dilse-release"
keychain_service="DilSe Android Release Keystore"

if [[ -f "${keystore_path}" || -f "${properties_path}" ]]; then
    printf 'Signing files already exist. Nothing was changed.\n' >&2
    printf 'Keystore: %s\n' "${keystore_path}" >&2
    exit 1
fi

if ! command -v keytool >/dev/null 2>&1; then
    printf 'keytool is required. Install Android Studio or a Java 17 JDK first.\n' >&2
    exit 1
fi

signing_password="$(openssl rand -hex 24)"

keytool -genkeypair \
    -keystore "${keystore_path}" \
    -storepass "${signing_password}" \
    -keypass "${signing_password}" \
    -alias "${key_alias}" \
    -keyalg RSA \
    -keysize 4096 \
    -validity 10000 \
    -dname "CN=baatdilse.com, OU=Mobile, O=DilSe, C=CA" \
    -noprompt

printf '%s\n' \
    "storePassword=${signing_password}" \
    "keyPassword=${signing_password}" \
    "keyAlias=${key_alias}" \
    "storeFile=../dilse-release.jks" > "${properties_path}"

if command -v security >/dev/null 2>&1; then
    security add-generic-password \
        -a "${USER}" \
        -s "${keychain_service}" \
        -w "${signing_password}" \
        -U >/dev/null
fi

unset signing_password
printf 'Created the DilSe release key and local signing configuration.\n'
printf 'Back up this file before publishing: %s\n' "${keystore_path}"
printf 'The password is stored in macOS Keychain as: %s\n' "${keychain_service}"
