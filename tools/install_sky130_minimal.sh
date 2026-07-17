#!/usr/bin/env bash
set -euo pipefail

TARGET_ROOT="${1:-sky130-pdk}"
PR_COMMIT="403964dc7f9cca5ec1a8cc7b4f2a6f532b781676"
HD_COMMIT="9cb2d7cb8ed4619094263614039a61b6b2d22a88"

install_sparse_repo() {
  local url="$1"
  local commit="$2"
  local destination="$3"
  shift 3

  if [[ -d "${destination}/.git" ]]; then
    current="$(git -C "${destination}" rev-parse HEAD)"
    if [[ "${current}" != "${commit}" ]]; then
      echo "Existing checkout at ${destination} has commit ${current}, expected ${commit}." >&2
      exit 1
    fi
    return
  fi

  mkdir -p "$(dirname "${destination}")"
  git clone --filter=blob:none --no-checkout "${url}" "${destination}"
  git -C "${destination}" sparse-checkout init --cone
  git -C "${destination}" sparse-checkout set "$@"
  git -C "${destination}" fetch --depth 1 origin "${commit}"
  git -C "${destination}" checkout --detach "${commit}"
}

install_sparse_repo \
  "https://github.com/fossi-foundation/skywater-pdk-libs-sky130_fd_pr.git" \
  "${PR_COMMIT}" \
  "${TARGET_ROOT}/libraries/sky130_fd_pr/latest" \
  cells/nfet_01v8 cells/pfet_01v8_hvt

install_sparse_repo \
  "https://github.com/fossi-foundation/skywater-pdk-libs-sky130_fd_sc_hd.git" \
  "${HD_COMMIT}" \
  "${TARGET_ROOT}/libraries/sky130_fd_sc_hd/latest" \
  cells/inv cells/nand2 cells/nor2 cells/xor2 cells/a21oi cells/o21ai cells/mux2 cells/nand3

echo "SKY130 minimal checkout installed under ${TARGET_ROOT}."
echo "Primitive commit: ${PR_COMMIT}"
echo "HD-library commit: ${HD_COMMIT}"
