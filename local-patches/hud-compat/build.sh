#!/usr/bin/env bash
set -euo pipefail
patch_dir=$(cd -- "$(dirname -- "$0")" && pwd)
launcher_libraries=/home/cyberbot/.local/share/FreesmLauncher/libraries
build_classes=$(mktemp -d /tmp/hud-compat-build.XXXXXX)
compile_classpath="$launcher_libraries/org/spongepowered/mixin/0.8.5/mixin-0.8.5.jar"
compile_classpath+=":$launcher_libraries/net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar"
compile_classpath+=":$launcher_libraries/net/minecraftforge/javafmllanguage/1.20.1-47.4.10/javafmllanguage-1.20.1-47.4.10.jar"
mapfile -t java_sources < <(find "$patch_dir/src" -type f -name '*.java' | sort)
javac -proc:none --release 17 -cp "$compile_classpath" -d "$build_classes" "${java_sources[@]}"
cp -a "$patch_dir/resources/." "$build_classes/"
mkdir -p "$patch_dir/build"
jar --create --file "$patch_dir/build/combatroll-hudfix-1.1.1.jar" \
    --manifest "$patch_dir/resources/META-INF/MANIFEST.MF" -C "$build_classes" .
unzip -tq "$patch_dir/build/combatroll-hudfix-1.1.1.jar"
printf '%s\n' "$patch_dir/build/combatroll-hudfix-1.1.1.jar"
