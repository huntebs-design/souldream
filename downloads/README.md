# Android releases

`DilSe-latest.apk` is produced by `scripts/build_android_release.sh`. Keep the
APK signed with the same release key for every version so Android accepts it as
an update to an existing installation. The APK and its checksum are deliberately
excluded from Git.
