# UniSat — Software Bill of Materials

**Generated:** 2026-04-17T22:08:46Z
**Branch:** feat/trl5-hardening
**Commit:** 21b95e0

## Python dependencies

### flight-software

- "sgp4>=2.22"
- "numpy>=1.26.0"
- "pyserial>=3.5"
- "Pillow>=10.1.0"
- "aiofiles>=23.2.0"

### ground-station

- streamlit>=1.30.0
- plotly>=5.18.0
- pandas>=2.1.0
- numpy>=1.26.0
- sgp4>=2.22
- pydeck>=0.8.0
- Pillow>=10.0.0

## C / C++ / Assembly dependencies (firmware)

These libraries are fetched at build time (not committed) via
`scripts/setup_stm32_hal.sh` and `scripts/setup_freertos.sh`.
Pinned tags:

| Name | Source | Pinned tag | License | Fetched by |
|------|--------|------------|---------|------------|
| STM32CubeF4 HAL | github.com/STMicroelectronics/STM32CubeF4 | v1.27.1 | SLA0044 (BSD-3-Clause variant) | `scripts/setup_stm32_hal.sh` |
| CMSIS Core (ARM) | from STM32CubeF4 bundle | same | Apache-2.0 | `scripts/setup_stm32_hal.sh` |
| FreeRTOS Kernel | github.com/FreeRTOS/FreeRTOS-Kernel | V10.6.1 | MIT | `scripts/setup_freertos.sh` |
| CMSIS-RTOSv2 wrapper | from STM32CubeF4 bundle | v1.27.1 | Apache-2.0 | `scripts/setup_freertos.sh` |
| Unity (test framework) | ThrowTheSwitch/Unity | in-tree header-only | MIT | vendored in `firmware/tests/unity/` |

## CI Docker image

`docker/Dockerfile.ci` builds on an official Ubuntu base. See the
Dockerfile for the pinned digest.

## Links

- Full SPDX JSON (syft-generated, if available): `sbom-full.spdx.json`
- Summary table (syft-generated, if available): `sbom-summary.txt`
