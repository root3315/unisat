# UniSat — Полная техническая документация

**Версия:** 1.3.1 — Universal Platform polish (14 форм-факторов, form-factor registry как единый источник правды)
**Дата:** Апрель 2026
**Лицензия:** Apache License, Version 2.0 (ранее MIT до 2026-04-18)
**Репозиторий:** https://github.com/root3315/unisat

**Что нового с v1.2.0:**
- **v1.3.0** — универсальная платформа: реестр форм-факторов (`form_factors.py`), feature-flag резолвер (`feature_flags.py`), compile-time профили firmware через `mission_profile.h` (9 билд-целей `make target-<profile>`), Streamlit profile gate.
- **v1.3.1** — configurator-валидаторы подключены к `core.form_factors` (единый источник правды вместо параллельных словарей), CanSat-масштабные дефолты компонентов, 5 новых configurator-шаблонов, `docs/OPERATIONS_GUIDE.md` (12 секций от выбора профиля до сдачи на конкурс), фикс flaky `test_long_soak`.

---

## Содержание

0. [TRL-5 hardening (Phase 1–8) — что нового с v1.0](#0-trl-5-hardening-phase-18)
1. [Что такое UniSat](#1-что-такое-unisat)
2. [Поддерживаемые платформы](#2-поддерживаемые-платформы)
3. [Структура проекта](#3-структура-проекта)
4. [Быстрый старт](#4-быстрый-старт)
5. [Архитектура системы](#5-архитектура-системы)
6. [Модули flight-software](#6-модули-flight-software)
7. [Core-модули](#7-core-модули)
8. [Firmware (STM32)](#8-firmware-stm32)
9. [Наземная станция](#9-наземная-станция)
10. [Симуляторы](#10-симуляторы)
11. [Payload модули](#11-payload-модули)
12. [Конфигуратор миссии](#12-конфигуратор-миссии)
13. [Тестирование](#13-тестирование)
14. [CanSat: подробное руководство](#14-cansat-подробное-руководство)
15. [CubeSat: подробное руководство](#15-cubesat-подробное-руководство)
16. [Docker](#16-docker)
17. [Конкурсы и адаптация](#17-конкурсы-и-адаптация)

---

## 0. TRL-5 hardening (Phase 1–8)

С момента первой публикации (v1.0, 2026-04-15) проект прошёл
8 фаз software hardening на ветке `feat/trl5-hardening`. Эта
секция описывает, что добавилось и где искать детали.

### Новые модули (firmware)

| Модуль | Файл | Назначение | Тесты |
|---|---|---|:---:|
| **Target build infra** | `firmware/stm32/Target/` | LD script, startup.s, SystemInit, clock cfg, IT handlers, HAL shim, FreeRTOSConfig.h, stm32f4xx_hal_conf.h, stm32_assert.h, peripherals.c | build |
| **command_dispatcher** | `Core/Src/command_dispatcher.c` | HMAC-SHA256 + 32-bit counter + 64-bit sliding replay window | 11 |
| **key_store** | `Core/Src/key_store.c` | A/B flash slots + CRC + monotonic generation | 10 |
| **fdir** | `Core/Src/fdir.c` | 12-fault advisor, escalation window, 6-level severity ladder | 9 |
| **mode_manager** | `Core/Src/mode_manager.c` | Commander layer — enacts SAFE/DEGRADED/REBOOT transitions | 9 |
| **fdir_persistent** | `Core/Src/fdir_persistent.c` | `.noinit` SRAM ring buffer survives warm reboot + CRC | 6 |
| **board_temp** | `Drivers/BoardTemp/board_temp.c` | TMP117 facade for beacon bytes 14-15 (Tboard) | 6 |
| **boot_security** (integration) | `main.c` | Wires key_store → dispatcher at boot, fail-closed | 4 |

### Python side additions

| Что | Где | Тесты |
|---|---|:---:|
| **CounterSender** (ground-side) | `ground-station/utils/hmac_auth.py` | 22 |
| **E2E mission scenario** | `flight-software/tests/test_mission_e2e.py` | 3 |
| **Long-soak harness** (gated via env var) | `flight-software/tests/test_long_soak.py` | 1 |
| **Streamlit page smoke** | `ground-station/tests/test_pages_smoke.py` | 13 |
| **Extended coverage packs** | `flight-software/tests/test_*_coverage.py`, `*_extended.py`, `*_mocked.py` | 75+ |

### Документация — новые артефакты

| Файл | Содержит |
|---|---|
| `docs/requirements/SRS.md` | Software Requirements Spec, 44 REQ, priority + verification + source + test pointers |
| `docs/requirements/traceability.csv` | Machine-readable REQ → source → test matrix |
| `docs/reliability/fdir.md` | FDIR policy — fault table + severity ladder + thresholds |
| `docs/quality/static_analysis.md` | cppcheck + coverage + sanitizers policy |
| `docs/characterization/` | WCET / stack / heap / power measurement templates |
| `docs/testing/hil_test_plan.md` | HIL bench BOM ($155) + 10 test IDs |
| `docs/adr/ADR-003..008.md` | Architecture decisions: A/B keystore, counter=0 sentinel, FDIR split, .noinit, HAL shim, dispatcher wire format |
| `docs/sbom/sbom-summary.md` | Auto-generated Software Bill of Materials |
| `NOTICE` | Apache-2.0 third-party attribution |

### Quality gates — все зелёные

| Gate | Команда | Результат |
|---|---|---|
| C ctest | `make test-c` | 27/27 |
| Python pytest | `make test-py` | 314+ passing |
| C line coverage | `make coverage` | 85.3 % |
| Python coverage | `make coverage-py` | 85.15 % (gate ≥ 80 %) |
| cppcheck gate | `make cppcheck` | clean |
| ASAN + UBSAN | `make sanitizers` | 27/27 clean |
| STRICT (-Werror) | `cmake -DSTRICT=ON` | 27/27 |
| mypy strict | `make lint-py` | 0 issues в 21 файле |
| **ARM .elf builds** | `make setup-all && make target` | **31.6 KB flash (6 %) / 36.3 KB RAM (28 %)** |
| SBOM | `make sbom` | SPDX summary под `docs/sbom/` |

### Новые make targets

```bash
# Setup (one-time)
make setup-all            # fetches HAL + FreeRTOS (~15 MB)

# Target build
make target               # cross-compile .elf / .bin / .hex
make size                 # per-section flash/RAM report
make flash                # st-flash to Nucleo-F446RE

# Quality gates
make cppcheck             # static-analysis (CI-blocking)
make cppcheck-strict      # + MISRA advisory report
make coverage             # C lcov HTML + % metric
make coverage-py          # Python pytest-cov + 80 % gate
make sanitizers           # ASAN + UBSAN
make lint-py              # mypy --strict

# Extras
make sbom                 # SPDX bill of materials
make configurator         # Streamlit mission configurator UI
```

### Security model (actual)

Две угрозы из `docs/security/ax25_threat_model.md` закрыты
полностью:

**T1 — Command injection.** HMAC-SHA256 authenticates every uplink
frame. `CCSDS_Dispatcher_Submit` drops unauthenticated frames
silently (no NAK, no timing oracle). Constant-time verify per
`hmac_sha256_verify`. Key epoch = 32 bytes, RFC 4231-compliant.

**T2 — Replay.** 32-bit monotonic counter prepended to authenticated
body; firmware maintains a 64-bit sliding-window bitmap and rejects
duplicates, too-old frames, and counter=0 (reserved sentinel —
see ADR-004). Ground-side `CounterSender` is thread-safe and
monotonic; 8×100-thread race test verifies no duplicate values.

**Key management.** A/B flash slots with CRC-32 + magic-byte
validation. Generation counter strictly increasing so an
attacker replaying an older "rotate key" command cannot
downgrade. Torn-write safe: mid-rotation power-loss leaves the
previously-active slot intact (ADR-003).

### Reliability (FDIR) — NASA-style three-tier

```
L0 HW         → watchdog IC, voltage supervisor
L1 SW         → Error_Handler + Watchdog_CheckAll + fdir.c advisor
L1.5 Supervisor→ mode_manager.c (polls FDIR @ 1 Hz, enacts transitions)
L1.6 Persistent→ fdir_persistent.c (.noinit ring buffer + CRC)
L2 Ground     → operator TC next pass (~90 min)
```

12 fault IDs, 6-level severity ladder (LOG_ONLY → RETRY →
RESET_BUS → DISABLE_SUBSYS → SAFE_MODE → REBOOT), 60-second
escalation window. See `docs/reliability/fdir.md` for the fault
table + threshold rationale.

### License migration

Проект первоначально был под **MIT (2026-02-15 — 2026-04-18)**.
С 2026-04-18 — **Apache License 2.0**. Причина: patent-grant
clause (§3) и defensive-termination (§3 последний абзац). Копии,
полученные в MIT-окне, остаются под MIT — это фундаментальное
свойство open-source лицензий.

---

---

## 1. Что такое UniSat

UniSat — это универсальная модульная программная платформа для аэрокосмических аппаратов. Проект покрывает полный стек ПО: от прошивки микроконтроллера STM32 до наземной станции с веб-интерфейсом.

### Статистика проекта

| Метрика | Значение |
|---------|----------|
| Файлов в репозитории | 217 |
| Строк кода | 26,232 |
| Python файлов | 90 |
| C файлов (header + source) | 60 |
| Тест-файлов | 34 |
| Тестов (pytest) | 139 passing |
| Линтер | ruff clean (0 ошибок) |
| Документов (docs/) | 15+ файлов |
| Payload модулей | 7 |
| Mission templates | 5 |

### Что входит в проект

- **Firmware** (C + FreeRTOS) — прошивка для STM32F446RE бортового компьютера
- **Flight Software** (Python + asyncio) — полётный контроллер для Raspberry Pi
- **Ground Station** (Streamlit + Plotly) — наземная станция с 10 страницами
- **Simulation** (Python + numpy) — 10 симуляторов (орбита, энергия, термо, связь, NDVI, IGRF)
- **Configurator** (Streamlit) — веб-конфигуратор миссии с валидацией
- **Payloads** — 7 сменных модулей полезной нагрузки
- **Hardware** — KiCad схемы, BOM, механические спецификации

---

## 2. Поддерживаемые платформы

UniSat поддерживает 6 типов аэрокосмических аппаратов:

### 2.1 CubeSat (орбитальный спутник)

| Форм-фактор | Размеры (мм) | Макс. масса | Солн. панели | Назначение |
|-------------|--------------|-------------|-------------|------------|
| 1U | 100 × 100 × 113.5 | 1.33 кг | 4 | Образование, технодемо |
| 2U | 100 × 100 × 227.0 | 2.66 кг | 4 | Технодемо |
| 3U | 100 × 100 × 340.5 | 4.00 кг | 6 | ДЗЗ, наука |
| 6U | 100 × 226.3 × 340.5 | 12.00 кг | 8 | Полная миссия |
| 12U | 226.3 × 226.3 × 340.5 | 24.00 кг | 10 | Тяжёлая нагрузка |

**Орбита:** LEO 400-700 км, SSO (97.6°), ISS (51.6°)
**Период:** ~96 мин, ~15 витков/сутки
**Срок жизни:** 2-10 лет (зависит от высоты)

### 2.2 CanSat (атмосферный зонд)

| Параметр | Значение |
|----------|----------|
| Внешний диаметр | 68 мм |
| Внутренний диаметр | 64 мм |
| Высота | 80 мм |
| Макс. масса | 500 г |
| Толщина стенки | 2 мм |
| Форма | Цилиндр (банка из-под газировки) |

**Высота сброса:** 300-1000 м
**Скорость спуска:** 6-11 м/с (по регламенту)
**Время полёта:** 30-120 секунд
**Телеметрия:** минимум 100 отсчётов

### 2.3 Ракета (суборбитальная)

| Параметр | Значение |
|----------|----------|
| Размер авионики | 50 × 50 × 100 мм |
| Макс. масса авионики | 500 г |
| Целевая высота | 3048 м (10,000 ft) |
| Режим спасения | Dual deploy (drogue + main) |

### 2.4 Стратосферный аэростат (HAB)

| Параметр | Значение |
|----------|----------|
| Размер payload box | 200 × 200 × 150 мм |
| Макс. масса | 1.5 кг |
| Целевая высота | 30,000 м |
| Скорость подъёма | ~5 м/с |

### 2.5 Дрон (UAV)

| Параметр | Значение |
|----------|----------|
| Размер платформы | 400 × 400 × 200 мм |
| Макс. масса | 2.5 кг |
| Макс. высота | 120 м |
| Время полёта | 30 мин |

### 2.6 Custom (пользовательский)

Полностью настраиваемая платформа — все параметры задаются в `mission_config.json`.

---

## 3. Структура проекта

```
unisat/
├── firmware/                  # Прошивка STM32F446RE (C + FreeRTOS)
│   ├── CMakeLists.txt         # Система сборки
│   ├── stm32/
│   │   ├── Core/Inc/          # 13 заголовочных файлов
│   │   ├── Core/Src/          # 12 файлов реализации
│   │   ├── Drivers/           # 8 HAL-драйверов сенсоров
│   │   ├── ADCS/              # Алгоритмы ориентации (4 файла)
│   │   └── EPS/               # Энергосистема (3 модуля)
│   └── tests/                 # Тесты (Unity framework)
│
├── flight-software/           # Полётный контроллер (Python 3.11+)
│   ├── flight_controller.py   # Главный контроллер
│   ├── run_cansat.py          # Запуск CanSat симуляции
│   ├── core/                  # Ядро: EventBus, StateMachine, Registry
│   ├── modules/               # 16 модулей подсистем
│   └── tests/                 # pytest тесты
│
├── ground-station/            # Наземная станция (Streamlit)
│   ├── app.py                 # Главное приложение
│   ├── pages/                 # 10 страниц (01-10)
│   └── utils/                 # Декодеры, парсеры, визуализация
│
├── simulation/                # Симуляторы
│   ├── orbit_simulator.py     # Орбита (Кеплер + J2)
│   ├── power_simulator.py     # Энергобаланс
│   ├── thermal_simulator.py   # Тепловая модель
│   ├── link_budget_calculator.py  # Бюджет радиолинии
│   ├── ndvi_analyzer.py       # NDVI вегетационный индекс
│   ├── igrf_model.py          # Геомагнитное поле Земли
│   ├── cloud_detector.py      # Детектор облачности
│   ├── analytical_solutions.py # Аналитические решения
│   ├── mission_analyzer.py    # Комплексный анализ миссии
│   └── visualize.py           # Генерация графиков
│
├── configurator/              # Веб-конфигуратор миссии
│   ├── configurator_app.py    # Streamlit UI
│   ├── validators/            # Валидаторы (масса, энергия, объём)
│   ├── generators/            # Генераторы конфигов и отчётов
│   └── templates/             # Шаблоны форм-факторов
│
├── payloads/                  # Сменные модули полезной нагрузки
│   ├── radiation_monitor/     # Дозиметр (SBM-20)
│   ├── earth_observation/     # Мультиспектральная камера
│   ├── iot_relay/             # IoT ретранслятор (LoRa)
│   ├── magnetometer_survey/   # Магнитосъёмка
│   ├── spectrometer/          # Оптический спектрометр
│   └── cansat_descent/        # Контроллер спуска (парашют)
│
├── mission_templates/         # Готовые конфигурации миссий
│   ├── cansat_standard.json
│   ├── cubesat_sso.json
│   ├── rocket_competition.json
│   ├── hab_standard.json
│   └── drone_survey.json
│
├── hardware/                  # Схемы и механика
│   ├── kicad/                 # Электрические схемы
│   ├── mechanical/            # 3D модели
│   └── bom/                   # Перечень компонентов
│
├── docker/                    # Dockerfiles
├── notebooks/                 # Скрипты анализа данных
├── docs/                      # CDR-документация (15+ файлов)
├── scripts/                   # Утилиты (setup, test, flash)
├── mission_config.json        # Главный конфиг миссии
├── docker-compose.yml         # Docker Compose
└── README.md                  # Описание проекта (EN + RU)
```

---

## 4. Быстрый старт

### 4.1 Требования

- Python 3.11+
- Git
- pip
- (опционально) ARM GCC toolchain для firmware
- (опционально) Docker

### 4.2 Установка

```bash
# Клонировать
git clone https://github.com/root3315/unisat.git
cd unisat

# Установить зависимости
pip install -r flight-software/requirements.txt
pip install -r ground-station/requirements.txt
pip install -r simulation/requirements.txt
pip install pytest

# Или всё сразу
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

### 4.3 Запуск тестов

```bash
# Все Python тесты
python -m pytest flight-software/tests/ ground-station/tests/ -v

# Результат: 139 passed
```

### 4.4 Запуск CanSat симуляции

```bash
cd flight-software
python run_cansat.py --config ../mission_templates/cansat_standard.json --max-altitude 500
```

### 4.5 Запуск наземной станции

```bash
cd ground-station
pip install -r requirements.txt
streamlit run app.py
# Открыть http://localhost:8501
```

### 4.6 Запуск конфигуратора

```bash
cd configurator
pip install -r requirements.txt
streamlit run configurator_app.py
# Открыть http://localhost:8501
```

### 4.7 Запуск симуляции миссии

```bash
cd simulation
python mission_analyzer.py        # Полный анализ
python analytical_solutions.py    # Аналитические решения
python ndvi_analyzer.py           # NDVI анализ
```

### 4.8 Сборка firmware

```bash
# Нужен ARM toolchain
sudo apt install gcc-arm-none-eabi cmake
cd firmware && mkdir build && cd build
cmake .. && make -j$(nproc)

# Прошивка через ST-Link
../scripts/flash_stm32.sh
```

---

## 5. Архитектура системы

### 5.1 Общая архитектура

```
┌─────────────────────────────────────────────────────────┐
│                 НАЗЕМНАЯ СТАНЦИЯ                         │
│    Streamlit (10 страниц) / Plotly / HMAC-SHA256        │
└──────────────────────┬──────────────────────────────────┘
                       │ UHF 437 МГц / S-band 2.4 ГГц
                       │ AX.25 / CCSDS протокол
┌──────────────────────┴──────────────────────────────────┐
│              ПОЛЁТНЫЙ КОНТРОЛЛЕР (RPi Zero 2 W)          │
│  EventBus ←→ StateMachine ←→ ModuleRegistry              │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐     │
│  │Camera  │ │Orbit   │ │Health  │ │  Scheduler   │     │
│  │Handler │ │Predict │ │Monitor │ │  (asyncio)   │     │
│  └────────┘ └────────┘ └────────┘ └──────────────┘     │
└──────────────────────┬──────────────────────────────────┘
                       │ UART 115200 baud
┌──────────────────────┴──────────────────────────────────┐
│              OBC FIRMWARE (STM32F4 + FreeRTOS)           │
│  6 задач: Sensor | Telemetry | Comm | ADCS | WDT | Pay │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐     │
│  │ADCS  │ │EPS   │ │COMM  │ │GNSS  │ │Telemetry │     │
│  │B-dot │ │MPPT  │ │UHF   │ │u-blox│ │  CCSDS   │     │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 5.2 EventBus (шина событий)

Все модули общаются через EventBus — publish/subscribe система:

```python
# Модуль публикует событие
await event_bus.emit("sensor.imu.update", data={"accel_g": 5.2}, source="imu")

# Другой модуль подписан и реагирует
event_bus.subscribe("sensor.*", handle_sensor_data)
```

Модули не знают друг о друге напрямую — полная изоляция.

### 5.3 StateMachine (автомат состояний)

Для каждой платформы свой набор фаз:

**CubeSat:** `startup → deployment → detumbling → commissioning → nominal → science → safe_mode`

**CanSat:** `pre_launch → launch_detect → ascent → apogee → descent → landed`

**Ракета:** `pre_launch → powered_ascent → coast → apogee → drogue_descent → main_descent → landed`

Переходы между фазами происходят автоматически по событиям (IMU детектирует ускорение, барометр — высоту) или по таймеру.

### 5.4 ModuleRegistry (реестр модулей)

Динамически загружает модули из `mission_config.json`:

```python
registry.load_modules_from_config(config,
    core_modules=profile.core_modules,      # обязательные
    optional_modules=profile.optional_modules  # опциональные
)
await registry.initialize_all()  # инициализация
await registry.start_all()       # запуск
```

---

## 6. Модули flight-software

### 6.1 Таблица всех модулей

| Модуль | Файл | Назначение | Платформы |
|--------|------|-----------|-----------|
| **TelemetryManager** | `telemetry_manager.py` | Пакетирование данных в CCSDS, временные метки | Все |
| **DataLogger** | `data_logger.py` | Запись телеметрии в SQLite, CSV экспорт, ротация | Все |
| **HealthMonitor** | `health_monitor.py` | Мониторинг CPU, RAM, температуры, диска | Все |
| **CommunicationManager** | `communication.py` | UART, радиоканал, HMAC-SHA256 аутентификация | Все |
| **PowerManager** | `power_manager.py` | Энергобюджет, приоритетное отключение нагрузок | Все |
| **SafeModeHandler** | `safe_mode.py` | Аварийный режим при потере связи или низком заряде | Все |
| **TaskScheduler** | `scheduler.py` | Планировщик задач (периодические, по событию, по орбите) | Все |
| **CameraHandler** | `camera_handler.py` | Съёмка по расписанию и по команде | CubeSat, CanSat |
| **ImageProcessor** | `image_processor.py` | SVD сжатие, JPEG, геопривязка, миниатюры | CubeSat |
| **OrbitPredictor** | `orbit_predictor.py` | SGP4, TLE, предсказание пролётов, eclipse | CubeSat |
| **IMUSensor** | `imu_sensor.py` | MPU9250 акселерометр + гироскоп, детекция старта | CanSat, Ракета |
| **BarometricAltimeter** | `barometric_altimeter.py` | BME280, высота по давлению | CanSat, HAB, Ракета |
| **DescentController** | `descent_controller.py` | Управление парашютом, детекция апогея | CanSat, Ракета |
| **GNSSReceiver** | `gnss_receiver.py` | u-blox GPS, координаты, скорость | Все |
| **PayloadInterface** | `payload_interface.py` | Базовый класс для payload, RadiationPayload, NullPayload | Все |

### 6.2 Как работает каждый модуль

#### TelemetryManager
Собирает данные со всех датчиков и пакетирует в формат CCSDS:
- Primary Header (6 байт): версия, тип, APID, sequence count, длина
- Secondary Header (10 байт): timestamp, subsystem ID
- Data Field (переменная длина): полезные данные
- CRC-16 (2 байта): контрольная сумма

```python
tm = TelemetryManager()
packet = tm.build_packet(apid=0x001, data=sensor_bytes)
```

#### PowerManager
Следит за энергобалансом и отключает нагрузки при низком заряде:
- SOC > 30%: всё работает
- SOC 15-30%: отключаются Camera, S-band, Payload
- SOC < 15%: остаются только OBC и COMM

```python
pm = PowerManager()
pm.update(solar_w=4.5, battery_soc=25.0)  # сработает load shedding
```

#### SafeModeHandler
Включается автоматически при:
- Потере связи на 24 часа (настраивается)
- Критически низком заряде
- Перегреве
- Сбое watchdog

В safe mode: beacon каждые 30 секунд, все нагрузки отключены кроме COMM.

#### DescentController (CanSat/Ракета)
Управляет раскрытием парашюта:
1. IMU детектирует невесомость (< 0.3g) → апогей
2. Активирует servo/burn wire для раскрытия
3. Контролирует скорость спуска
4. Детектирует посадку

#### IMUSensor
MPU9250 — 9-DOF инерциальный модуль:
- Акселерометр: ±2/4/8/16g
- Гироскоп: ±250/500/1000/2000 °/с
- Магнитометр: ±4800 µT

Детектирует:
- Запуск (ускорение > 3g)
- Апогей (невесомость < 0.3g)
- Посадку (удар)

---

## 7. Core-модули

### 7.1 EventBus (`core/event_bus.py`)

Async pub/sub для межмодульной коммуникации:

```python
bus = EventBus()

# Подписка (поддерживает wildcards)
bus.subscribe("sensor.*", my_handler)
bus.subscribe("phase.descent.enter", on_descent)

# Публикация
await bus.emit("sensor.imu.update", data={"accel": 5.2}, source="imu")
```

### 7.2 StateMachine (`core/state_machine.py`)

Конфигурируемый автомат состояний:
- Фазы загружаются из MissionProfile
- Валидированные переходы (только разрешённые)
- Timeout-based авто-переходы
- Guards (проверки перед переходом)
- Включение/отключение модулей по фазам

### 7.3 ModuleRegistry (`core/module_registry.py`)

Динамическая загрузка модулей:
- Загружает по имени из `mission_config.json`
- Инициализирует, запускает, останавливает
- Отслеживает ошибки инициализации
- Предоставляет `get_module("name")` для получения

### 7.4 MissionTypes (`core/mission_types.py`)

570 строк профилей для 10 типов миссий:
- `PlatformCategory`: cubesat, cansat, rocket, hab, drone, custom
- `MissionType`: cubesat_leo, cubesat_sso, cansat_standard, cansat_advanced, rocket_competition, hab_standard, drone_survey...
- `MissionProfile`: фазы, модули, телеметрия, ограничения

---

## 8. Firmware (STM32)

### 8.1 Микроконтроллер

| Параметр | Значение |
|----------|----------|
| MCU | STM32F446RE |
| Ядро | ARM Cortex-M4 @ 180 МГц |
| Flash | 512 КБ |
| SRAM | 128 КБ |
| FPU | Есть (single precision) |
| RTOS | FreeRTOS |

### 8.2 FreeRTOS задачи

| Задача | Приоритет | Стек | Период | Функция |
|--------|----------|------|--------|---------|
| WatchdogTask | 5 (высший) | 256 слов | 1 сек | Мониторинг задач, feed IWDG |
| CommTask | 4 | 1024 слов | 100 мс | UART TX/RX, beacon |
| SensorTask | 3 | 512 слов | 1 сек | Чтение всех датчиков |
| ADCSTask | 3 | 1024 слов | По очереди | Алгоритмы ориентации |
| TelemetryTask | 2 | 512 слов | По очереди | Пакетирование CCSDS |
| PayloadTask | 1 (низший) | 512 слов | 5 сек | Сбор данных payload |

### 8.3 Подключённые датчики

| Датчик | Интерфейс | Адрес | Что измеряет |
|--------|-----------|-------|-------------|
| LIS3MDL | I2C | 0x1C | Магнитное поле (3 оси) |
| BME280 | I2C | 0x76 | Температура, давление, влажность |
| TMP117 | I2C | 0x48 | Прецизионная температура (±0.1°C) |
| MPU9250 | SPI | CS=PA4 | Акселерометр + гироскоп + магнитометр |
| SBM20 | GPIO | Импульсы | Радиация (Гейгер) |
| u-blox MAX-M10S | I2C | 0x42 | GPS координаты |
| MCP3008 | SPI | CS=PA5 | АЦП 10 бит, 8 каналов (датчики Солнца) |
| Sun Sensors | через MCP3008 | CH0-5 | Освещённость на 6 гранях |

### 8.4 ADCS алгоритмы

| Алгоритм | Файл | Назначение |
|----------|------|-----------|
| B-dot Detumbling | `bdot.c` | Гашение вращения после отделения. M = -k × dB/dt |
| Sun Pointing | `sun_pointing.c` | Ориентация панелей на Солнце. PD-регулятор |
| Target Pointing | `target_pointing.c` | Наведение камеры на цель. PID + десатурация |
| Quaternion Math | `quaternion.c` | Полная библиотека кватернионов (multiply, inverse, normalize, Euler↔DCM) |

### 8.5 EPS (Энергосистема)

| Модуль | Файл | Функция |
|--------|------|---------|
| MPPT | `mppt.c` | Perturb & Observe — отслеживание максимума мощности |
| Battery Manager | `battery_manager.c` | SOC мониторинг, защита от пере/недозаряда |
| Power Distribution | `power_distribution.c` | Приоритетное включение/отключение подсистем |

### 8.6 Сборка firmware

```bash
# Кросс-компиляция для STM32
cd firmware && mkdir build && cd build
cmake .. && make

# Для хост-тестов (без железа)
cmake -DSIMULATION_MODE=ON .. && make
```

---

## 9. Наземная станция

### 9.1 Страницы

| # | Страница | Описание |
|---|----------|----------|
| 01 | Dashboard | Общий статус миссии, здоровье подсистем (🟢🟡🔴) |
| 02 | Telemetry | Графики в реальном времени: температура, напряжение, радиация |
| 03 | Orbit Tracker | 3D глобус с трассой полёта и положением спутника |
| 04 | Image Viewer | Галерея снимков с геопривязкой на карте |
| 05 | ADCS Monitor | Кватернион, углы Эйлера, индикаторы маховиков |
| 06 | Power Monitor | Gauge батареи, графики генерация vs потребление |
| 07 | Command Center | Отправка команд с HMAC-SHA256 аутентификацией |
| 08 | Mission Planner | Расписание пролётов, планирование съёмки |
| 09 | Data Export | Скачивание телеметрии в CSV/JSON/CCSDS |
| 10 | Health Report | Обнаружение аномалий, рекомендации |

### 9.2 Запуск

```bash
cd ground-station
pip install -r requirements.txt
streamlit run app.py
```

По умолчанию работает с demo-данными. Для подключения к реальному железу — настроить COM-порт в sidebar.

---

## 10. Симуляторы

### 10.1 Полный список

| Симулятор | Файл | Что считает |
|----------|------|------------|
| Orbit | `orbit_simulator.py` | Кеплер + J2, ground track, lat/lon/alt |
| Power | `power_simulator.py` | Eclipse/sunlight, генерация панелей, SOC батареи |
| Thermal | `thermal_simulator.py` | 6 граней: солнце + альбедо + IR + космос |
| Link Budget | `link_budget_calculator.py` | Friis, FSPL, SNR, BER, margin для UHF и S-band |
| NDVI | `ndvi_analyzer.py` | Вегетационный индекс из мультиспектрального снимка |
| IGRF | `igrf_model.py` | Геомагнитное поле Земли (дипольная модель IGRF-13) |
| Cloud | `cloud_detector.py` | Детекция облаков по яркости + NDSI |
| Analytical | `analytical_solutions.py` | Точные решения: период, SSO, eclipse, Хоманн, deorbit |
| Mission | `mission_analyzer.py` | Комплексный анализ (орбита + энергия + связь) |
| Visualize | `visualize.py` | Plotly графики: ground track, power budget, thermal |

### 10.2 Запуск

```bash
cd simulation
python mission_analyzer.py        # Всё сразу
python analytical_solutions.py    # Аналитика (для олимпиад)
python orbit_simulator.py         # Только орбита
python ndvi_analyzer.py           # NDVI (для NASA Space Apps)
```

---

## 11. Payload модули

### 11.1 Список payload

| Payload | Директория | Датчик | Назначение |
|---------|-----------|--------|-----------|
| Radiation Monitor | `radiation_monitor/` | SBM-20 (Гейгер) | Дозиметрия, мкЗв/ч |
| Earth Observation | `earth_observation/` | IMX219 (8MP) | Мультиспектральные снимки |
| IoT Relay | `iot_relay/` | SX1276 (LoRa) | Ретрансляция IoT сообщений |
| Magnetometer Survey | `magnetometer_survey/` | LIS3MDL | Магнитосъёмка Земли |
| Spectrometer | `spectrometer/` | AS7265x (18-ch) | Оптическая спектрометрия |
| CanSat Descent | `cansat_descent/` | Servo + парашют | Управление спуском |

### 11.2 Как создать свой payload

```python
from modules.payload_interface import PayloadInterface, PayloadSample

class MyPayload(PayloadInterface):
    def __init__(self, config=None):
        super().__init__("my_payload", config)

    async def initialize(self) -> bool:
        # Инициализация датчика
        return True

    def collect_sample(self) -> PayloadSample:
        # Считать данные
        return PayloadSample(
            timestamp=time.time(),
            payload_type="my_payload",
            data={"value": 42}
        )

    def shutdown(self) -> None:
        # Выключить датчик
        pass
```

---

## 12. Конфигуратор миссии

Веб-приложение для настройки миссии без кода:

```bash
cd configurator && streamlit run configurator_app.py
```

### Возможности:
- Выбор платформы (CubeSat / CanSat / Ракета / HAB / Дрон)
- Выбор форм-фактора и mission type
- Включение/отключение подсистем
- Автоматическая валидация: масса, энергия, объём
- Генерация `mission_config.json`
- Конкурс-специфичные параметры (скорость спуска, высота и т.д.)

---

## 13. Тестирование

### 13.1 Запуск тестов

```bash
# Все тесты
python -m pytest flight-software/tests/ ground-station/tests/ -v

# Конкретный модуль
python -m pytest flight-software/tests/test_safe_mode.py -v

# С покрытием
python -m pytest --cov=flight-software --cov-report=html

# Линтер
ruff check flight-software/ ground-station/ simulation/ configurator/
```

### 13.2 Что тестируется

| Область | Файлы | Тестов | Что проверяется |
|---------|-------|--------|----------------|
| Event Bus | test_event_bus.py | ~15 | Pub/sub, wildcards, async handlers |
| State Machine | test_state_machine.py | ~18 | Переходы, guards, timeouts, все платформы |
| Mission Types | test_mission_types.py | ~10 | Профили для 5 платформ |
| New Modules | test_new_modules.py | ~15 | IMU, барометр, descent controller |
| Power Manager | test_power_manager.py | ~13 | Load shedding, emergency, OBC protection |
| Safe Mode | test_safe_mode.py | ~15 | Entry/exit, beacon, recovery, comm timeout |
| Payload | test_payload_interface.py | ~12 | Lifecycle, samples, NullPayload |
| CCSDS Parser | test_ccsds_parser.py | ~5 | CRC, roundtrip, corruption |
| Telemetry Decoder | test_decoder.py | ~4 | OBC/beacon decode, short data |
| Flight Controller | test_flight_controller.py | ~3 | Init, CanSat profile, system status |
| Configurator | test_validators.py | ~14 | Mass/power/volume для каждого форм-фактора |
| **Итого** | **~34 файла** | **139** | |

---

## 14. CanSat: подробное руководство

### 14.1 Что такое CanSat

CanSat — это мини-спутник размером с банку газировки. Запускается ракетой или с дрона на высоту 300-1000 м, спускается на парашюте, собирая данные.

### 14.2 Как запустить CanSat миссию

```bash
cd flight-software

# Базовый запуск (высота 500м, спуск 8 м/с)
python run_cansat.py --config ../mission_templates/cansat_standard.json

# С параметрами
python run_cansat.py --max-altitude 800 --descent-rate 7.0 --launch-delay 5
```

### 14.3 Фазы полёта CanSat

```
PRE_LAUNCH → LAUNCH_DETECT → ASCENT → APOGEE → DESCENT → LANDED
     │             │            │         │         │         │
  Калибровка    IMU > 3g     Барометр   IMU      Парашют    SD карта
  датчиков      старт       считает    < 0.3g   раскрыт    сохранена
                            высоту    невесомость  8 м/с
```

### 14.4 Модули для CanSat

- **IMU** (обязательный) — детектирует старт и апогей
- **Barometer** (обязательный) — высота по давлению
- **Descent Controller** (обязательный) — парашют
- **GNSS** (рекомендуемый) — координаты для поиска
- **COMM** (обязательный) — передача на землю
- **Telemetry** (обязательный) — пакетирование данных
- **Payload** (опционально) — твой эксперимент

### 14.5 Размеры и масса

| Параметр | Значение | Примечание |
|----------|----------|------------|
| Внешний диаметр | 68 мм | Корпус |
| Внутренний диаметр | 64 мм | Полезное пространство |
| Высота | 80 мм | |
| Макс масса | 500 г | С парашютом |
| Стенка | 2 мм | Алюминий или 3D печать |
| Объём внутренний | ~257 см³ | Для электроники |

---

## 15. CubeSat: подробное руководство

### 15.1 Как запустить CubeSat миссию

```bash
# Полная симуляция миссии
cd simulation
python mission_analyzer.py

# Наземная станция
cd ground-station
streamlit run app.py
```

### 15.2 Подсистемы CubeSat

| Подсистема | Модули | Мощность (Вт) |
|-----------|--------|---------------|
| OBC | STM32F446RE + RPi Zero 2 W | 0.5 (ном) |
| EPS | MPPT + 4×18650 + солн. панели | 0.15 |
| COMM UHF | CC1125, 437 МГц, 9600 бпс | 1.0-1.5 |
| COMM S-band | 2.4 ГГц, 256 кбпс | 2.0-2.5 |
| ADCS | 3 магниторкера + 3 маховика | 0.8-1.2 |
| GNSS | u-blox MAX-M10S | 0.3 |
| Camera | IMX219 (8MP, 30м GSD) | 2.0-3.0 |
| Payload | SBM-20 / LoRa / спектрометр | 0.5-0.8 |

### 15.3 Энергобаланс (3U, 550 км SSO)

| Параметр | Значение |
|----------|----------|
| Генерация (среднее по орбите) | 3.6 Вт (BOL) / 3.3 Вт (EOL) |
| Потребление (номинал) | 2.57 Вт |
| Потребление (наука) | 6.46 Вт |
| Потребление (safe mode) | 1.21 Вт |
| Батарея | 30 Вт·ч (4S1P NCR18650B) |
| Баланс за орбиту | +0.84 Вт·ч (номинал) |

---

## 16. Docker

### 16.1 Запуск через Docker Compose

```bash
# Всё сразу
docker compose up -d

# Наземная станция: http://localhost:8501
# Конфигуратор: http://localhost:8502
```

### 16.2 Отдельные контейнеры

```bash
# Только наземная станция
docker compose up ground-station

# Только симуляция
docker compose run simulation
```

---

## 17. Конкурсы и адаптация

### 17.1 Какой конкурс — какой конфиг

| Конкурс | Template | Ключевое |
|---------|----------|----------|
| CanSat | `cansat_standard.json` | Парашют, IMU, барометр, 500г |
| CubeSat Design | `cubesat_sso.json` | Полная документация CDR |
| NASA Space Apps | `cubesat_sso.json` + NDVI | `simulation/ndvi_analyzer.py` |
| Ракетный конкурс | `rocket_competition.json` | Dual deploy, высотомер |
| HAB | `hab_standard.json` | Стратосферный полёт |
| Хакатон | Любой | Быстрый старт через конфигуратор |
| Олимпиада | — | `simulation/analytical_solutions.py` |

### 17.2 Как адаптировать

1. Выбрать шаблон из `mission_templates/`
2. Открыть конфигуратор: `streamlit run configurator/configurator_app.py`
3. Настроить параметры под регламент
4. Скачать `mission_config.json`
5. Запустить: `python flight-software/run_cansat.py --config mission_config.json`

---

## 18. AX.25 Link Layer (Track 1)

Полноценный link-layer для UHF-канала по стандарту AX.25 v2.2.
Реализован с нуля: C11 pure-library + Python зеркало + SITL-демо.

### 18.1 Модульное дерево

```
firmware/stm32/Drivers/AX25/
├── ax25_types.h       — ax25_address_t, ax25_ui_frame_t,
│                        ax25_status_t (10 error codes),
│                        ax25_decoder_t (stateful decoder)
├── ax25.h / .c        — pure API: FCS, bit-stuff, address,
│                        encode_ui_frame, decode_ui_frame
├── ax25_decoder.h/.c  — streaming decoder:
│                        init, reset, push_byte (bit-level SM)
└── ax25_api.h         — AX25_Xxx() facade for project-style
                         callers (ADR-002)

ground-station/utils/ax25.py        — Python mirror, stdlib only
ground-station/cli/ax25_listen.py   — TCP server, decodes frames
ground-station/cli/ax25_send.py     — TCP client, encodes frame
tests/golden/ax25_vectors.json      — 28 shared test vectors
tests/golden/ax25_vectors.inc       — C include version
```

### 18.2 Wire format

```
0x7E [Dst 7B] [Src 7B] 0x03 0xF0 [Info ≤256B] [FCS 2B LE] 0x7E
 │    │        │         │    │     │            │          │
 │    callsign<<1 +      │    │     CCSDS        CRC-16     flag
 │    SSID byte (§3.12)  │    PID  Space         /X.25
 │                       UI   0xF0 Packet
 └─ HDLC flag              Ctrl (no L3)
```

Body (everything between flags) is bit-stuffed: after 5 consecutive
1-bits a 0-bit is inserted so a byte-aligned `0x7E` never appears
mid-frame. See `ax25_bit_stuff` / `ax25_bit_unstuff` in `ax25.c`.

### 18.3 Streaming decoder data flow

```
ISR:   HAL_UART_Receive_IT
         └─> COMM_UART_RxCallback(byte)
               └─> ring buffer push (lock-free)

Task:  comm_rx_task (FreeRTOS, 10 ms period, priority above-normal)
         └─> COMM_ProcessRxBuffer()
               └─> ax25_decoder_push_byte()
                     ├─ HUNT: search for 0x7E opening flag
                     └─ FRAME:
                         ├─ read 8 bits LSB-first
                         ├─ drop stuff bit after 5 ones
                         ├─ reject 6 consecutive ones
                         └─ on closing 0x7E → decode_ui_frame
                                             → CCSDS dispatcher
```

Декодер **никогда не выполняется в interrupt context** (REQ-AX25-019).
ISR делает только single-byte push в ring buffer (512 B), что даёт
427 ms headroom на 9600 bps.

### 18.4 API примеры

**Encode (C, firmware):**
```c
#include "ax25_api.h"

AX25_Address_t dst = { .callsign = "CQ",     .ssid = 0 };
AX25_Address_t src = { .callsign = "UN8SAT", .ssid = 1 };
uint8_t frame[AX25_MAX_FRAME_BYTES];
uint16_t n = 0;

if (AX25_EncodeUiFrame(&dst, &src, 0xF0,
                        info, info_len,
                        frame, sizeof(frame), &n)) {
    COMM_Send(COMM_CHANNEL_UHF, frame, n);
}
```

**Decode (C, firmware):**
```c
static AX25_Decoder_t dec;
AX25_DecoderInit(&dec);

AX25_UiFrame_t frame;
bool ready = false;
AX25_DecoderPushByte(&dec, byte_from_uart, &frame, &ready);
if (ready) {
    /* frame.info is the CCSDS Space Packet payload */
}
```

**Encode/decode (Python, ground):**
```python
from utils.ax25 import Address, encode_ui_frame, Ax25Decoder

wire = encode_ui_frame(Address("CQ", 0), Address("UN8SAT", 1),
                        0xF0, b"hello")

dec = Ax25Decoder()
for b in wire:
    frame = dec.push_byte(b)
    if frame:
        print(frame.info, frame.fcs_valid)
```

### 18.5 Cross-validation (REQ-AX25-015)

C и Python реализации обязаны давать **байт-идентичный результат**
на всех 28 golden vectors. Автоматически проверяется:

- C:      `firmware/tests/test_ax25_golden.c`
- Python: `ground-station/tests/test_ax25.py::TestGoldenVectors`

Если в C или Python появится регрессия, один из раннеров провалит
один и тот же вектор. Разработчик сразу видит расхождение.

---

## 19. HMAC-SHA256 Command Auth (Track 1b)

Криптографические примитивы для аутентификации CCSDS-команд.

### 19.1 Модули

```
firmware/stm32/Drivers/Crypto/
├── sha256.h / .c          — FIPS 180-4 SHA-256, streaming API
└── hmac_sha256.h / .c     — RFC 2104 HMAC + constant-time verify

ground-station/utils/hmac_auth.py  — hashlib-backed Python mirror

firmware/tests/test_hmac.c         — RFC 4231 §4.2, §4.3 vectors
```

### 19.2 Гарантии

- **FIPS 180-4 корректность:** SHA-256 даёт канонический хеш
  `e3b0c442...b855` на пустом входе и `ba7816bf...15ad` на `"abc"`.
- **RFC 4231 совместимость:** HMAC-SHA256 повторяет тестовые
  векторы §4.2 и §4.3.
- **Constant-time verification:** `hmac_sha256_verify` не
  зависит от входа по времени — защита от timing side-channel.
- **Нет зависимостей:** всё на `<stdint.h>` + `<string.h>`.
  Готов для flight-software, не требует heap.
- **Python согласован побайтно:** тот же RFC 4231 тест в pytest.

### 19.3 Применение (план интеграции)

```c
/* TX (firmware): */
uint8_t cmd[CCSDS_MAX_PACKET_SIZE];
uint16_t n = CCSDS_Serialize(&packet, cmd, sizeof(cmd));
uint8_t tag[HMAC_SHA256_TAG_SIZE];
hmac_sha256(SHARED_KEY, KEY_LEN, cmd, n, tag);
memcpy(&cmd[n], tag, HMAC_SHA256_TAG_SIZE);
COMM_SendAX25(..., cmd, n + HMAC_SHA256_TAG_SIZE);

/* RX (firmware, in the dispatcher — Track 1b wiring): */
uint8_t expected[HMAC_SHA256_TAG_SIZE];
hmac_sha256(SHARED_KEY, KEY_LEN, frame.info,
             frame.info_len - HMAC_SHA256_TAG_SIZE, expected);
if (!hmac_sha256_verify(
        expected, &frame.info[frame.info_len - HMAC_SHA256_TAG_SIZE])) {
    /* drop silently, increment auth-fail counter */
    return;
}
/* dispatch authenticated command */
```

См. `docs/security/ax25_threat_model.md` (T1, T2) для полного
threat-model'а и remaining work.

---

## 20. SITL Demo

Полный путь "C-кодер → TCP → Python-декодер" работает локально и в CI.

### 20.1 Запуск в Docker

```bash
# 1. Собрать CI image (один раз, ~30 сек):
docker build -f docker/Dockerfile.ci -t unisat-ci .

# 2. Собрать firmware (Linux-host) и прогнать demo:
docker run --rm -v "$(pwd):/work" -w /work unisat-ci bash -lc "
  cd firmware && cmake -B build -S . && cmake --build build &&
  ctest --test-dir build --output-on-failure &&
  python3 scripts/demo.py --port 52100
"
```

Ожидаемый вывод:

```
[sitl_fw] connecting to 127.0.0.1:52100
[sitl_fw] sent beacon 1 (69 bytes)
[demo] beacon 1: 000102030405060708090a0b0c0d0e0f...
[sitl_fw] sent beacon 2 (69 bytes)
[demo] beacon 2: 101112131415161718191a1b1c1d1e1f...
[demo] SUCCESS — 2 beacons decoded
```

### 20.2 Что именно проверяется

- **C `AX25_EncodeUiFrame`** собирает валидный AX.25 frame
  (flag, адреса §3.12, control/PID, info, FCS CRC-16/X.25, flag).
- **C `VirtualUART_Send`** кросс-платформенно (POSIX sockets /
  Winsock) отправляет байты в TCP-канал.
- **Python `ax25_listen.py`** принимает TCP-поток, кормит его
  побайтно в `Ax25Decoder`.
- **Python `Ax25Decoder`** реассемблирует фрейм, проверяет FCS,
  эмитит JSON с `fcs_valid: true`.
- **`scripts/demo.py`** читает JSON, валидирует что пришло
  ровно 2 beacon'а, `exit 0` на успех.

Фактически это end-to-end proof что C и Python договариваются на
уровне одного бита на реальном (loopback) wire'е.

---

## 21. Тестовое покрытие

### 21.1 C tests (`ctest`)

```
 1: beacon_layout        — Telemetry_PackBeacon 48-byte layout
 2: ax25_fcs             — CRC-16/X.25 oracle "123456789"→0x906E
 3: ax25_bitstuff        — bit-level stuffing, byte boundaries
 4: ax25_address         — callsign<<1, SSID, H-bit (§3.12)
 5: ax25_frame           — encode+pure decode roundtrip, error paths
 6: ax25_golden          — 28 shared vectors vs Python
 7: ax25_decoder         — streaming: single, idle, back-to-back,
                           recovery, 10k fuzz
 8: ax25_api             — project-style facade smoke
 9: comm_integration     — ring → decoder → CCSDS dispatcher
10: virtual_uart_build   — SITL TCP shim
11: ccsds                — CCSDS packet CRC, sequence, roundtrip
12: adcs_algorithms      — quaternion math, B-dot
13: eps                  — MPPT, battery SOC, charge protection
14: telemetry_placeholder— telemetry test hook
15: hmac                 — RFC 4231 §4.2-4.3, SHA-256 FIPS 180-4
```

**Итого: 15 targets, all green.** Покрытие включает каждую из
подсистем (OBC, ADCS, EPS, COMM, GNSS через integration, Payload
через SBM20, Crypto).

### 21.2 Python tests (`pytest`)

34 tests в `ground-station/tests/test_ax25.py`:

- **Unit:** FCS, bit-stuffing, address, UI-frame (18 тестов)
- **Golden vectors:** 28 shared with C (3 test cases)
- **Streaming:** decoder, idle flags, back-to-back, recovery
  (4 tests)
- **Hypothesis:** 200 property-based roundtrips + 500 fuzz
  cases (2 tests)
- **HMAC:** RFC 4231 §4.2, §4.3, constant-time verify (3 tests)

### 21.3 Cross-validation

C tests и Python tests **разделяют fixture** (`tests/golden/
ax25_vectors.*`). Python генератор — `scripts/gen_golden_vectors.py`
— single source of truth. Если C или Python разойдутся, golden runner
на одной из сторон упадёт.

---

*Документация обновлена: Апрель 2026 (v1.3.1 — Universal Platform polish)*
