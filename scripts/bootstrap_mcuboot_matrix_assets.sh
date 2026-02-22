#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ZEPHYR_REF="${ZEPHYR_REF:-v3.7.0}"
ZEPHYR_WS="${ZEPHYR_WS:-${REPO_ROOT}/third_party/zephyr_ws}"
ZEPHYR_VENV="${ZEPHYR_VENV:-${REPO_ROOT}/third_party/zephyr-venv}"
TOOLCHAIN_PATH="${GNUARMEMB_TOOLCHAIN_PATH:-$HOME/tools/gcc-arm-none-eabi-8-2018-q4-major}"
ASSETS_DIR="${OSS_ASSETS_DIR:-${REPO_ROOT}/results/oss_validation/assets}"
BUILD_DIR="${OSS_BUILD_DIR:-${REPO_ROOT}/results/oss_validation/build}"
HELLO_BUILD_DIR="${HELLO_BUILD_DIR:-${BUILD_DIR}/hello_world_mcuboot}"
SLOT_SIZE="${SLOT_SIZE:-0x76000}"
HEADER_SIZE="${HEADER_SIZE:-0x200}"
ALIGN="${ALIGN:-8}"
MARKER_FILE="${BUILD_DIR}/.mcuboot_bootstrap_done"

SLOT0="${ASSETS_DIR}/zephyr_slot0_padded.bin"
SLOT1="${ASSETS_DIR}/zephyr_slot1_padded.bin"

if [[ ! -d "${REPO_ROOT}/third_party" ]]; then
    mkdir -p "${REPO_ROOT}/third_party"
fi
mkdir -p "${ASSETS_DIR}" "${BUILD_DIR}"

if [[ ! -x "${ZEPHYR_VENV}/bin/west" ]]; then
    python3 -m venv "${ZEPHYR_VENV}"
    "${ZEPHYR_VENV}/bin/pip" install --upgrade pip
    "${ZEPHYR_VENV}/bin/pip" install west
fi

if [[ ! -d "${ZEPHYR_WS}/.west" ]]; then
    "${ZEPHYR_VENV}/bin/west" init -m "https://github.com/zephyrproject-rtos/zephyr" --mr "${ZEPHYR_REF}" "${ZEPHYR_WS}"
fi

# Keep the workspace venv aligned with Zephyr build-time Python deps (e.g. pyelftools).
if [[ -f "${ZEPHYR_WS}/zephyr/scripts/requirements.txt" ]]; then
    "${ZEPHYR_VENV}/bin/pip" install -r "${ZEPHYR_WS}/zephyr/scripts/requirements.txt"
fi

if [[ -f "${ZEPHYR_WS}/bootloader/mcuboot/scripts/requirements.txt" ]]; then
    "${ZEPHYR_VENV}/bin/pip" install -r "${ZEPHYR_WS}/bootloader/mcuboot/scripts/requirements.txt"
fi

if [[ ! -f "${MARKER_FILE}" || "${FORCE_BOOTSTRAP:-0}" == "1" ]]; then
    (
        cd "${ZEPHYR_WS}"
        if [[ "${SKIP_WEST_UPDATE:-0}" != "1" ]]; then
            "${ZEPHYR_VENV}/bin/west" update --narrow -o=--depth=1
        fi
        if command -v ninja >/dev/null 2>&1; then
            "${ZEPHYR_VENV}/bin/west" config build.generator "Ninja"
        else
            "${ZEPHYR_VENV}/bin/west" config build.generator "Unix Makefiles"
        fi
    )
fi

if [[ ! -x "${TOOLCHAIN_PATH}/bin/arm-none-eabi-gcc" ]]; then
    echo "missing toolchain at ${TOOLCHAIN_PATH}" >&2
    exit 1
fi

if [[ ! -f "${SLOT0}" || ! -f "${SLOT1}" || "${FORCE_REBUILD_SLOTS:-0}" == "1" ]]; then
    (
        cd "${ZEPHYR_WS}"
        export ZEPHYR_TOOLCHAIN_VARIANT=gnuarmemb
        export GNUARMEMB_TOOLCHAIN_PATH="${TOOLCHAIN_PATH}"
        "${ZEPHYR_VENV}/bin/west" build \
            -d "${HELLO_BUILD_DIR}" \
            -p always \
            -b nrf52840dk/nrf52840 \
            "zephyr/samples/hello_world" \
            -- \
            -DCONFIG_BOOTLOADER_MCUBOOT=y \
            -DCMAKE_GDB:FILEPATH="${TOOLCHAIN_PATH}/bin/arm-none-eabi-gdb" \
            -DPython3_EXECUTABLE:FILEPATH="${ZEPHYR_VENV}/bin/python3"
    )

    IMGTOOL="${ZEPHYR_WS}/bootloader/mcuboot/scripts/imgtool.py"
    KEY_FILE="${ZEPHYR_WS}/bootloader/mcuboot/root-rsa-2048.pem"
    SOURCE_BIN="${HELLO_BUILD_DIR}/zephyr/zephyr.bin"

    python3 "${IMGTOOL}" sign \
        --key "${KEY_FILE}" \
        --header-size "${HEADER_SIZE}" \
        --align "${ALIGN}" \
        --slot-size "${SLOT_SIZE}" \
        --version "1.0.0" \
        "${SOURCE_BIN}" \
        "${SLOT0}"

    python3 "${IMGTOOL}" sign \
        --key "${KEY_FILE}" \
        --header-size "${HEADER_SIZE}" \
        --align "${ALIGN}" \
        --slot-size "${SLOT_SIZE}" \
        --version "1.0.1" \
        "${SOURCE_BIN}" \
        "${SLOT1}"
fi

touch "${MARKER_FILE}"

echo "slot image A: ${SLOT0}"
echo "slot image B: ${SLOT1}"
