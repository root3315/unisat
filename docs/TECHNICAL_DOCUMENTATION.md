# UniSat — Полная техническая документация

**Версия:** 1.0.0
**Дата:** Апрель 2026
**Репозиторий:** https://github.com/root3315/unisat

---

## Содержание

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

*Документация обновлена: Апрель 2026*
