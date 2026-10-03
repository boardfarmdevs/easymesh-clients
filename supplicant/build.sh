#!/usr/bin/env bash
# Build the client (wpa_supplicant 2.12 with the patch series) and the bench's
# access point (stock hostapd 2.12) from the release tarballs in sources.env,
# from clean source trees every time.
#
#   supplicant/build.sh [--tarballs DIR] [--work DIR] [--output DIR] [--reference] [--iwd]
#
#   --tarballs DIR  where the tarballs are kept or fetched to (default supplicant/tarballs)
#   --work DIR      where the source trees are unpacked (default supplicant/work)
#   --output DIR    where the programs and build.env go (default supplicant/build)
#   --reference     also build the RDK lab's wpa_supplicant 2.10, as
#                   wpa_supplicant-2.10 (bench test B12)
#   --iwd           also build iwd 3.12 for the linux-iwd model (bench test B11)
#
# Needs a C toolchain, pkg-config, and the libnl-3, libnl-genl-3, libnl-route-3,
# OpenSSL, D-Bus and (for iwd) readline development files. The programs are
# never committed; build.env records what they were built from.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source-path=SCRIPTDIR source=sources.env
. "$HERE/sources.env"
TARBALLS=$HERE/tarballs
WORK=$HERE/work
OUTPUT=$HERE/build
REFERENCE=0
IWD=0
while [ $# -gt 0 ]; do
    case $1 in
        --tarballs) TARBALLS=${2:?--tarballs DIR}; shift ;;
        --work) WORK=${2:?--work DIR}; shift ;;
        --output) OUTPUT=${2:?--output DIR}; shift ;;
        --reference) REFERENCE=1 ;;
        --iwd) IWD=1 ;;
        -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
        *) echo "usage: $0 [--tarballs DIR] [--work DIR] [--output DIR] [--reference] [--iwd]" >&2; exit 2 ;;
    esac
    shift
done
JOBS=$(nproc 2>/dev/null || echo 2)
mkdir -p "$TARBALLS" "$WORK" "$OUTPUT"

# fetch URL SHA256: the tarball's path, fetched once and always checked
fetch() {
    local url=$1 sum=$2 file
    file=$TARBALLS/$(basename "$url")
    if [ ! -f "$file" ]; then
        echo "fetching $url" >&2
        curl -fsSL -o "$file.part" "$url"
        mv "$file.part" "$file"
    fi
    echo "$sum  $file" | sha256sum -c --quiet - >&2 \
        || { echo "checksum mismatch: $file" >&2; exit 1; }
    echo "$file"
}

# unpack TARBALL NAME: a clean tree at WORK/NAME
unpack() {
    rm -rf "${WORK:?}/$2"
    mkdir -p "$WORK/$2"
    tar -xf "$1" -C "$WORK/$2" --strip-components=1
}

series_digest() {
    cat "$HERE"/patches/*.patch | sha256sum | cut -d' ' -f1
}

echo "== wpa_supplicant $WPA_SUPPLICANT_VERSION with the patch series"
tarball=$(fetch "$WPA_SUPPLICANT_URL" "$WPA_SUPPLICANT_SHA256")
unpack "$tarball" wpa_supplicant
for p in "$HERE"/patches/*.patch; do
    echo "applying $(basename "$p")"
    patch -d "$WORK/wpa_supplicant" -p1 -s --no-backup-if-mismatch < "$p"
done
cp "$WORK/wpa_supplicant/wpa_supplicant/defconfig" "$WORK/wpa_supplicant/wpa_supplicant/.config"
cat "$HERE/wpa_supplicant.config" >> "$WORK/wpa_supplicant/wpa_supplicant/.config"
make -C "$WORK/wpa_supplicant/wpa_supplicant" -j"$JOBS" -s wpa_supplicant wpa_cli
install -m 0755 "$WORK/wpa_supplicant/wpa_supplicant/wpa_supplicant" \
    "$WORK/wpa_supplicant/wpa_supplicant/wpa_cli" "$OUTPUT/"

echo "== hostapd $HOSTAPD_VERSION, stock"
tarball=$(fetch "$HOSTAPD_URL" "$HOSTAPD_SHA256")
unpack "$tarball" hostapd
cp "$WORK/hostapd/hostapd/defconfig" "$WORK/hostapd/hostapd/.config"
cat "$HERE/hostapd.config" >> "$WORK/hostapd/hostapd/.config"
make -C "$WORK/hostapd/hostapd" -j"$JOBS" -s hostapd hostapd_cli
install -m 0755 "$WORK/hostapd/hostapd/hostapd" "$WORK/hostapd/hostapd/hostapd_cli" "$OUTPUT/"

if [ "$REFERENCE" = 1 ]; then
    echo "== wpa_supplicant $REFERENCE_VERSION, the RDK lab's build"
    tarball=$(fetch "$REFERENCE_URL" "$REFERENCE_SHA256")
    unpack "$tarball" reference
    patch -d "$WORK/reference" -p1 -s --no-backup-if-mismatch \
        < "$HERE/reference/0001-wnm-select-hidden-bss-by-current-ssid.patch"
    cp "$HERE/reference/wpa_supplicant-$REFERENCE_VERSION.config" "$WORK/reference/wpa_supplicant/.config"
    make -C "$WORK/reference/wpa_supplicant" -j"$JOBS" -s wpa_supplicant
    install -m 0755 "$WORK/reference/wpa_supplicant/wpa_supplicant" \
        "$OUTPUT/wpa_supplicant-$REFERENCE_VERSION"
fi

if [ "$IWD" = 1 ]; then
    echo "== iwd $IWD_VERSION"
    tarball=$(fetch "$IWD_URL" "$IWD_SHA256")
    unpack "$tarball" iwd
    (cd "$WORK/iwd" && ./configure -q --disable-manual-pages --disable-systemd-service \
        --prefix=/usr --localstatedir=/var --sysconfdir=/etc >/dev/null)
    # the default target: it generates ell/ell.h, which single targets skip
    make -C "$WORK/iwd" -j"$JOBS" -s >/dev/null
    install -m 0755 "$WORK/iwd/src/iwd" "$WORK/iwd/client/iwctl" "$OUTPUT/"
    install -m 0644 "$WORK/iwd/src/iwd-dbus.conf" "$OUTPUT/"
fi

commit=$(git -C "$HERE" rev-parse HEAD 2>/dev/null || echo unknown)
dirty=$(git -C "$HERE" status --porcelain -- . 2>/dev/null | head -1 || true)
{
    echo "BUILT=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "REPOSITORY_COMMIT=$commit${dirty:+-dirty}"
    echo "WPA_SUPPLICANT_VERSION=$WPA_SUPPLICANT_VERSION"
    echo "WPA_SUPPLICANT_SHA256=$WPA_SUPPLICANT_SHA256"
    names=()
    for p in "$HERE"/patches/*.patch; do names+=("$(basename "$p")"); done
    echo "PATCH_SERIES=${names[*]}"
    echo "PATCH_SERIES_SHA256=$(series_digest)"
    echo "WPA_SUPPLICANT_OPTIONS=defconfig $(grep -E '^CONFIG_' "$HERE/wpa_supplicant.config" | tr '\n' ' ' | sed 's/ $//')"
    echo "HOSTAPD_VERSION=$HOSTAPD_VERSION"
    echo "HOSTAPD_SHA256=$HOSTAPD_SHA256"
    echo "HOSTAPD_OPTIONS=defconfig $(grep -E '^CONFIG_' "$HERE/hostapd.config" | tr '\n' ' ' | sed 's/ $//')"
    if [ "$REFERENCE" = 1 ]; then
        echo "REFERENCE_VERSION=$REFERENCE_VERSION"
        echo "REFERENCE_SHA256=$REFERENCE_SHA256"
    fi
    if [ "$IWD" = 1 ]; then
        echo "IWD_VERSION=$IWD_VERSION"
        echo "IWD_SHA256=$IWD_SHA256"
    fi
} > "$OUTPUT/build.env"
echo "== built into $OUTPUT"
"$OUTPUT/wpa_supplicant" -v | head -1
# hostapd -v exits 1 by design
{ "$OUTPUT/hostapd" -v 2>&1 || true; } | head -1
