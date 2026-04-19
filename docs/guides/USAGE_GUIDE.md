# UniSat — Complete Usage Guide

**От нуля до работающей миссии за 10 минут.**

Этот документ — пошаговое руководство по всем сценариям использования
платформы UniSat: выбор типа миссии (CanSat / CubeSat / HAB /
Rocket / Drone), подготовка окружения, запуск, кастомизация,
подача на конкурс.

---

## 0. TL;DR — самый быстрый путь

```bash
git clone https://github.com/root3315/unisat.git
cd unisat
./scripts/verify.sh      # 1) полная самопроверка в Docker
make demo                # 2) end-to-end SITL-демо AX.25
cd configurator && streamlit run configurator_app.py   # 3) визуальный конфигуратор
```

Если `verify.sh` печатает `✓ UniSat green. Ready to submit.` —
платформа работает на твоей машине, и можно идти дальше.

---

## 1. Кому это

| Ты | Что тебе подходит | Время до результата |
|---|---|---|
| Студент, первый CanSat | `mission_templates/cansat_standard.json` + flight-software симулятор | 1 вечер |
| CubeSat Design конкурс | `mission_templates/cubesat_sso.json` + configurator + CDR docs | 1 неделя |
| NASA Space Apps / хакатон | Любой темплейт + Streamlit UI + симуляция орбиты | 48 часов |
| Ракетный конкурс (Spaceport America etc.) | `mission_templates/rocket_competition.json` + dual-deploy | 2–3 дня |
| HAB / стратосферный шар | `mission_templates/hab_standard.json` + GNSS + камера | 1 день |
| Исследователь, готовит к реальному запуску | Всё выше + HIL тесты + CDR документация + flight heritage plan | Месяцы |

Если ты просто хочешь **понять как устроен спутник** — запусти
симуляцию (`cd simulation && python mission_analyzer.py`) и почитай
`docs/reference/TECHNICAL_DOCUMENTATION.md`.

---

## 2. Системные требования

### Обязательно

- **Git** — для клонирования
- **Python 3.11+** — для ground station, симуляции, configurator
- **Docker Desktop** — для воспроизводимой сборки firmware без
  установки gcc/cmake локально

### Опционально (если хочешь запустить firmware на железе)

- **ARM toolchain** (`arm-none-eabi-gcc`) — для прошивки STM32
- **STM32CubeProgrammer** или **OpenOCD + ST-Link** — для заливки
- **Hardware** — см. `hardware/` (BOM, KiCad схемы)

### Не нужно

- Локальный `gcc` / `cmake` — всё собирается в Docker
- Учётная запись на NASA Developer Portal (мы не используем)
- Платный GitHub Actions — CI снят, локальная проверка работает

---

## 3. Первый запуск (5 минут)

### Шаг 1. Клон и самопроверка

```bash
git clone https://github.com/root3315/unisat.git
cd unisat
./scripts/verify.sh
```

Что происходит:

1. Docker собирает образ `unisat-ci` (30 сек, один раз).
2. Внутри контейнера: `cmake` → `make` → `ctest` (28/28) → `pytest` (420/420 по всем 4 пакетам).
3. Запускается end-to-end SITL-демо: C-кодер шлёт AX.25-пакеты по
   TCP, Python-декодер принимает, сверяет CRC.

Ожидаемый финал: `✓ UniSat green. Ready to submit.`

### Шаг 2. Выбор миссии

Открой `configurator/` — визуальный помощник:

```bash
cd configurator
pip install -r requirements.txt
streamlit run configurator_app.py
```

В браузере откроется мастер. Выбираешь форм-фактор, настраиваешь
полезную нагрузку, получаешь `mission_config.json`.

Или напрямую возьми готовый темплейт:

```bash
cp mission_templates/cubesat_sso.json mission_config.json
```

### Шаг 3. Запуск ground station

```bash
cd ground-station
pip install -r requirements.txt
streamlit run app.py
```

Откроется веб-интерфейс с 10 страницами: Mission Dashboard,
Telemetry Charts, Orbit 3D, Command Center (HMAC-authenticated),
Image Gallery, Attitude Viz, Power Monitor, Pass Predictor, Data
Export, Health Report.

Демо-данные загрузятся из `ground-station/data/demo.db`.

---

## 4. Выбор типа миссии — детально

### 4.1 CanSat (атмосферный зонд в жестяной банке)

**Когда:** школьные/университетские CanSat чемпионаты.
**Форм-фактор:** диаметр 64 мм, высота 68 мм (банка), 80 мм
(капсула), масса ≤500 г.
**Запуск:** ракета/дрон/шар на 500–1000 м, парашютный спуск.

Файлы:

```
mission_templates/cansat_standard.json    # канонический конфиг
flight-software/run_cansat.py             # entry point
payloads/cansat_descent/                  # descent controller
simulation/analytical_solutions.py        # аналитика спуска
```

Запуск симуляции:

```bash
cp mission_templates/cansat_standard.json mission_config.json
cd flight-software
python run_cansat.py --config ../mission_config.json --sim
```

Типичный тест-полёт в симуляции занимает ~5 минут реального
времени, производит ~300 КБ телеметрии, 20 снимков.

### 4.2 CubeSat (1U / 2U / 3U / 6U / 12U)

**Когда:** NASA CSLI, университетские design challenges, реальные
CubeSat миссии.
**Форм-фактор:** 10×10×11.35 см × n юнитов.
**Орбита:** LEO 400–700 км, SSO 97.6° или ISS-release 51.6°.

Файлы:

```
mission_templates/cubesat_sso.json        # 3U на солнечно-синхронке
firmware/stm32/...                        # вся OBC-прошивка
ground-station/                           # полная наземная станция
docs/design/mission_design.md                    # CDR-level документация
```

Тут работает всё: firmware, flight-software, ground-station,
simulation, configurator. Это основной use-case.

### 4.3 HAB (High-Altitude Balloon)

**Когда:** стратосферные эксперименты (30–40 км), любительские
исследования.
**Форм-фактор:** латексный шар + pod ≤1 кг.
**Полёт:** 2–4 часа, дрейф до 200 км.

```
mission_templates/hab_standard.json
payloads/earth_observation/               # камера для стратосферы
simulation/orbit_simulator.py             # в HAB-режиме даёт
                                            ballistic trajectory
```

### 4.4 Rocket competition

**Когда:** Spaceport America Cup, FAR-Mars, университетские ракеты.
**Особенность:** dual-deploy recovery, апогей-детекция, высотомер.

```
mission_templates/rocket_competition.json
payloads/radiation/ или custom            # научная нагрузка
```

### 4.5 Drone / UAV payload

**Когда:** CanSat-like тесты на дроне, тренировочные полёты.

```
mission_templates/drone_survey.json
```

Использует тот же flight-software stack, но без парашюта и с GPS
waypoint navigation.

---

## 5. Полный рабочий цикл разработки

### 5.1 Построение прошивки

**Host-build (для host-тестов, без железа):**

```bash
make build       # cmake + cmake --build
make test-c      # ctest 25/25 (post-TRL-5)
make test-py     # pytest 56+ тестов
```

> **Note on pyserial / flight-software tests.** A full green pytest run on
> `flight-software/tests/` requires `pip install -r flight-software/requirements.txt`
> (pyserial is the one that trips this). Without it, the
> `CommunicationManager` tests auto-skip cleanly — they no longer abort
> collection. The rest of the suite (camera, module_registry, …) still
> runs end-to-end.

Или вручную:

```bash
cd firmware
cmake -B build -S .
cmake --build build
ctest --test-dir build --output-on-failure
```

**Cross-build для реального STM32F446 (после TRL-5 hardening):**

```bash
# Одной командой из корня проекта (нужен arm-none-eabi-gcc):
make setup-hal   # первый раз — fetch STM32Cube HAL (~15 MB)
make target      # cross-compile -> build-arm/unisat_firmware.{elf,bin,hex}
make size        # per-section flash / RAM report
make flash       # прошить через ST-Link (со 90% footprint-бюджетом)
```

**Quality gates (запустить локально перед PR):**

```bash
make cppcheck        # static-analysis gate (zero warnings)
make coverage        # lcov HTML report (≥ 80% lines target)
make sanitizers      # ASAN + UBSAN под ctest
cmake -DSTRICT=ON ...; make  # -Werror -Wshadow -Wconversion
```

### 5.2 Flight software

Python-слой поверх RPi Zero 2 W (или любого Linux):

```bash
cd flight-software
pip install -r requirements.txt
python main.py --config ../mission_config.json
```

В режиме симуляции данные от датчиков берутся из `simulation/`.

### 5.3 Ground station

Реальный приём данных через радио (если есть железо):

```bash
# Терминал 1: AX.25 listener на TCP
cd ground-station
python -m cli.ax25_listen --port 52100

# Терминал 2: подключить SDR к TCP-пайпу
# (rtl-sdr + gr-satellites + FSK demod → netcat 52100)
```

Или имитация приёма:

```bash
# Терминал 1: listener
python -m cli.ax25_listen --port 52100 --count 10

# Терминал 2: отправка одного frame'а
python -m cli.ax25_send --host 127.0.0.1 --port 52100 \
    --dst-call CQ --src-call UN8SAT --src-ssid 1 \
    --info-hex "48656c6c6f"
```

Streamlit UI:

```bash
streamlit run app.py       # http://localhost:8501
```

### 5.4 Симуляция

Прогон всех симуляторов разом:

```bash
cd simulation
pip install -r requirements.txt
python mission_analyzer.py --config ../mission_config.json
```

Индивидуально:

```bash
python orbit_simulator.py    # Keplerian + J2, 1 орбита за 2 сек
python power_simulator.py    # энергобаланс с eclipse/sunlight
python thermal_simulator.py  # 6-face thermal model
python link_budget_calculator.py
python igrf_model.py         # магнитное поле Земли для ADCS
python ndvi_analyzer.py      # NDVI для Earth observation payload
```

### 5.5 Командование с HMAC-аутентификацией

Ключ — 32 байта, задаётся один раз при boot'е.

На ground station:

```python
from utils.ax25 import Address, encode_ui_frame
from utils.hmac_auth import hmac_sha256

KEY = bytes.fromhex("0011..." * 4)  # 32 B pre-shared secret
command = b"\x03\xF0\x01"  # CCSDS APID=CMD, cmd_id=REBOOT
tag = hmac_sha256(KEY, command)
frame = encode_ui_frame(Address("UN8SAT", 1), Address("MYCALL", 0),
                         0xF0, command + tag)
# отправить frame по TCP/радио
```

На satellite (firmware):

```c
#include "command_dispatcher.h"

static uint8_t g_key[32] = { /* burned at manufacturing */ };

int main(void) {
    CommandDispatcher_SetKey(g_key, sizeof(g_key));
    CommandDispatcher_SetHandler(my_command_handler);
    /* ... */
}

static void my_command_handler(const uint8_t *packet, uint16_t len) {
    /* CCSDS-уже проверен dispatcher'ом, tag уже валидирован */
    uint8_t cmd_id = packet[2];
    switch (cmd_id) {
        case 0x01: OBC_SoftwareReset(); break;
        case 0x02: EPS_EmergencyShutdown(); break;
        /* ... */
    }
}
```

**Без валидного HMAC-тэга command отклоняется, счётчик
`rejected_bad_tag++`, ответа нет** — атакующий не отличает
отброшенный спуф от потерянной реальной команды.

---

## 6. Кастомизация под твою миссию

### 6.1 Mission config

`mission_config.json` управляет почти всем:

```json
{
  "mission_name": "MyFirstSat-1",
  "form_factor": "3U",
  "mass_kg": 3.8,
  "orbit": { "altitude_km": 550, "inclination_deg": 97.6 },
  "subsystems": {
    "obc": { "enabled": true },
    "eps": { "enabled": true, "solar_panels": 6 },
    "adcs": { "enabled": true, "magnetorquers": 3 },
    "comm": { "uhf_enabled": true, "sband_enabled": false },
    "gnss": { "enabled": true },
    "payload": { "enabled": true }
  },
  "payload_type": "earth_observation",
  "callsign": { "dst": "CQ", "src": "UN8SAT", "src_ssid": 1 }
}
```

Configurator (`streamlit run configurator/configurator_app.py`) —
визуальный редактор с валидацией (проверяет mass/power/volume
budgets перед сохранением).

### 6.2 Добавить свой payload

1. Создай папку `payloads/my_experiment/`
2. Реализуй интерфейс из `payloads/interface.py`:

```python
class PayloadInterface:
    def init(self, config): ...
    def activate(self): ...
    def deactivate(self): ...
    def read_data(self) -> bytes: ...
    def get_status(self) -> dict: ...
```

3. Зарегистрируй в `mission_config.json`:

```json
"payload_type": "my_experiment",
"payload_config": { "sample_rate_hz": 10 }
```

4. Flight-software загрузит модуль динамически через `importlib`.

### 6.3 Добавить свой sensor driver

См. `firmware/stm32/Drivers/` как шаблон. Паттерн:
- `*_Handle_t` с `void *i2c_handle` / `spi_handle`
- `*_Platform_*` weak-symbol hooks (переопределяются STM32 HAL)
- `*_Init / *_Read*` API с `*_Status_t` return codes
- `SIMULATION_MODE` ветка с константными ответами

Затем подключи в `sensors.c` по образцу LIS3MDL/MPU9250.

### 6.4 Свой CCSDS APID для telemetry

В `firmware/stm32/Core/Inc/ccsds.h`:

```c
#define APID_MY_EXPERIMENT  0x042
```

В `telemetry.c` добавь функцию `Telemetry_PackMyExperiment`,
вызови `CCSDS_BuildPacket` с новым APID. Ground station
автоматически распарсит — `ccsds.py::parse_packet()` смотрит
APID из заголовка.

---

## 7. Подача на конкурс

### 7.1 CanSat championship

1. Скачай регламент с сайта чемпионата.
2. `cp mission_templates/cansat_standard.json mission_config.json`
3. Отредактируй массу/размеры под регламент.
4. Распечатай `configurator/bom_generator.py` → PDF с BOM.
5. Сгенерируй mission report: `python scripts/gen_mission_report.py`
6. Прикрепи к заявке:
   - `mission_config.json`
   - BOM PDF
   - Mission Report PDF
   - Видео `./scripts/verify.sh` run (доказательство работающего софта)

### 7.2 CubeSat Design / NASA CSLI

1. Заполни CDR-level документацию на основе шаблонов:
   - `docs/design/mission_design.md`
   - `docs/budgets/power_budget.md`
   - `docs/budgets/mass_budget.md`
   - `docs/budgets/link_budget.md`
   - `docs/budgets/thermal_analysis.md`
   - `docs/budgets/orbit_analysis.md`
2. Адаптируй `docs/reference/REQUIREMENTS_TRACEABILITY.md` под свои
   требования.
3. Прикрепи `docs/verification/ax25_trace_matrix.md` — показывает
   формальное прослеживание requirements → tests.
4. Запусти `./scripts/verify.sh`, запиши на видео финал
   `✓ UniSat green. Ready to submit.`
5. Приложи full source (лучше ссылкой на GitHub tag'ed release).

### 7.3 NASA Space Apps hackathon

48-часовой хакатон — используй готовое:

```bash
git clone https://github.com/root3315/unisat.git
cd unisat
./scripts/verify.sh
cd configurator && streamlit run configurator_app.py
```

Доработай `payloads/earth_observation/` или напиши свой
NDVI-анализатор в `simulation/ndvi_analyzer.py`. За 48 часов
вполне реально получить готовый submission с живой демкой.

### 7.4 Университетская олимпиада

Смотри `simulation/analytical_solutions.py` — там задачи по
орбитальной механике, power budget, ADCS, с аналитическими
решениями (не численными) — идеально для олимпиадных защит.

---

## 8. Что делать, если что-то не работает

### `./scripts/verify.sh` падает на Docker build

Проверь что Docker Desktop запущен (иконка кита в трее, зелёная).
Если компьютер только что проснулся, часы в контейнере могут
разойтись с Debian security репозиторием — `Dockerfile.ci` это
переживает (`apt-get update || true`).

### `No tests were found` после cmake

Ты в неправильной директории. `ctest` должен быть в
`firmware/build`, не в корне.

### Streamlit не стартует

```bash
pip install --upgrade streamlit plotly
```

### Изменил код, тесты не видят

CMake кеширует. `make clean && make all` или
`rm -rf firmware/build && ./scripts/verify.sh`.

### Нужна Windows-специфичная инструкция

`verify.sh` работает на Windows Git Bash благодаря
`MSYS_NO_PATHCONV=1` внутри. Если что-то не так — используй WSL2
или PowerShell + прямые `docker run` команды из README.

### Остальное

См. `docs/guides/TROUBLESHOOTING.md`.

---

## 9. Структура репозитория для ориентации

```
unisat/
├── README.md              ← стартовая точка, бейджи и обзор
├── CHANGELOG.md           ← история версий
├── COMPETITION_GUIDE.md   ← адаптация под конкурсы (быстрая)
├── CONTRIBUTING.md
├── LICENSE                ← MIT
├── Makefile               ← make all / test / demo / ci
├── docker/
│   └── Dockerfile.ci      ← образ для воспроизводимых прогонов
│
├── firmware/              ← C firmware для STM32F446
│   ├── CMakeLists.txt
│   ├── tests/             ← 16 ctest targets
│   └── stm32/
│       ├── Core/          ← OBC, COMM, GNSS, telemetry, CCSDS
│       ├── Drivers/       ← 9 драйверов + AX25 + Crypto + VirtualUART
│       ├── ADCS/          ← B-dot, quaternion, sun/target pointing
│       └── EPS/           ← MPPT, battery manager
│
├── flight-software/       ← Python layer для RPi Zero 2 W
│   ├── main.py
│   ├── tests/             ← 14 unit-test файлов
│   └── modules/           ← camera, orbit predictor, health monitor
│
├── ground-station/        ← Streamlit + Plotly UI
│   ├── app.py             ← главная точка входа
│   ├── pages/             ← 10 страниц dashboard'а
│   ├── utils/
│   │   ├── ax25.py        ← AX.25 кодек (Python)
│   │   └── hmac_auth.py   ← HMAC-SHA256 зеркало
│   ├── cli/
│   │   ├── ax25_listen.py ← TCP listener
│   │   └── ax25_send.py   ← TCP sender
│   └── tests/             ← 82 pytest-теста (hypothesis + golden + profile-gate)
│
├── simulation/            ← 10 симуляторов
├── configurator/          ← web-конфигуратор миссии
├── payloads/              ← 5 шаблонов полезной нагрузки
├── mission_templates/     ← 5 готовых `mission_config.json`
├── hardware/              ← BOM, KiCad схемы, mechanical
├── notebooks/             ← Jupyter demo notebooks
├── tests/golden/          ← shared C/Python AX.25 vectors
│
├── docs/                  ← 23 документа
│   ├── TECHNICAL_DOCUMENTATION.md  ← полная тех. дока (1100+ строк)
│   ├── USAGE_GUIDE.md              ← этот файл
│   ├── TROUBLESHOOTING.md
│   ├── API_REFERENCE.md
│   ├── architecture.md
│   ├── mission_design.md           ← CDR-level design
│   ├── communication_protocol.md   ← CCSDS + AX.25 wire format
│   ├── power_budget.md
│   ├── mass_budget.md
│   ├── link_budget.md
│   ├── thermal_analysis.md
│   ├── orbit_analysis.md
│   ├── testing_plan.md
│   ├── assembly_guide.md
│   ├── REQUIREMENTS_TRACEABILITY.md
│   ├── POSTER_TEMPLATE.md
│   ├── adr/                         ← architectural decisions
│   │   ├── ADR-001-no-csp.md
│   │   └── ADR-002-style-adapter.md
│   ├── security/
│   │   └── ax25_threat_model.md
│   ├── tutorials/
│   │   └── ax25_walkthrough.md     ← byte-by-byte beacon разбор
│   ├── verification/
│   │   ├── ax25_trace_matrix.md    ← auto-gen req → test mapping
│   │   └── driver_audit.md          ← все 8 драйверов verified real
│   └── superpowers/                 ← design specs + plans
│
└── scripts/
    ├── verify.sh                    ← one-command reproducibility
    ├── demo.py                      ← SITL end-to-end
    ├── sitl_fw.c                    ← firmware side of SITL
    ├── gen_golden_vectors.py
    └── gen_trace_matrix.py
```

---

## 10. Следующие шаги после "работает"

1. Прочитай `docs/reference/TECHNICAL_DOCUMENTATION.md` целиком — там все
   детали архитектуры.
2. Прогони `notebooks/` — интерактивные демо в Jupyter.
3. Сделай свой CanSat в симуляции (1 час).
4. Подключи реальное железо (опционально, см. `hardware/`).
5. Подай на конкурс.

---

*Документ обновлён: Апрель 2026 · версия 1.1*
