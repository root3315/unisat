# Critical Design Review — CanSat «РадиоПрофиль-1»

**Миссия:** вертикальный профиль мощности дозы гамма-излучения в приземном слое атмосферы (0–500 м) с разрешением по высоте ≤ 10 м.

**Форм-фактор:** `cansat_standard` — Ø68 × 80 мм цилиндр, масса ≤ 500 г, CDS-compliant.

**Команда:** *[название команды]* · Контакт: *[email]* · Код: [github.com/root3315/unisat](https://github.com/root3315/unisat) v1.4.3

---

## 1. Концепция операций (ConOps)

```
t=0s   Ground checkout      → IMU + баро + GNSS fix, HMAC-auth установлена
t=Ns   Запуск (ракета/шар)  → IMU детектирует > 3 g → phase transition
t+30s  Ascent (~500 м)      → на пике IMU/баро фиксируют апогей
t+35s  Apogee / ejection    → сервопривод SG90 освобождает парашют
t+36s  Descent ~8 м/с       → СНАЧАЛА парашют, потом сбор данных:
                               - SBM-20 считает импульсы за 5 с окно
                               - барометр — высота до приземления
                               - GNSS — горизонтальный снос
t+95s  Landed               → CSV на SD + финальный beacon с координатами
```

Жизненный цикл полёта ~95 секунд от апогея до приземления.

---

## 2. Научная задача

Подробно в [`SCIENCE_MISSION.md`](SCIENCE_MISSION.md). Короткая версия:

1. Собрать **высотный профиль гамма-фона** от 0 до ~500 м с шагом ≤ 10 м.
2. Сопоставить измерения с теоретической моделью ослабления космической составляющей в нижней тропосфере.
3. Детектировать любые локальные аномалии (техногенные источники, грозовые зоны).

**Оригинальность:** большинство CanSat-команд делают telemetry-only. Радиационный профиль требует интеграции импульсного датчика (GPIO-капчур) и чёткой временной метки на каждом счёте — это усложняет и отличает проект.

---

## 3. Требования (RS)

| REQ-ID | Требование | Обоснование | Метод верификации |
|---|---|---|---|
| REQ-CSR-01 | Масса ≤ 500 г с точностью ±0.5 г | Регламент CanSat, п. 2 | Весы 0.1 г, pre-launch mass check |
| REQ-CSR-02 | Габариты Ø68 × 80 мм (CDS) | Регламент CanSat | Штангенциркуль, Ø60 мм внутр. обитаемый объём |
| REQ-CSR-03 | Скорость снижения 6–11 м/с | Регламент CanSat, п. 4 | SITL + drop-тест с квадрокоптера |
| REQ-CSR-04 | Телеметрия ≥ 100 сэмплов за миссию | Регламент CanSat | On-board logger @ 10 Hz × 95 s = 950 сэмплов |
| REQ-CSR-05 | Непрерывная работа ≥ 30 минут на батарее | Pre-launch + flight + post-flight | Bench-тест с LiPo 1000 мАч |
| REQ-SCI-01 | SBM-20 импульсы регистрируются с dead-time ≤ 100 мкс | Физика трубки | GPIO interrupt + 1 μs таймштамп |
| REQ-SCI-02 | Высотное разрешение профиля ≤ 10 м | Научная цель | При 8 м/с и 5 с окне → 40 м. **Цель: 1 с окно → 8 м** ✓ |
| REQ-SCI-03 | GNSS точность координат приземления ≤ 5 м | Recovery | u-blox MAX-M10S, multi-GNSS |
| REQ-SCI-04 | Данные сохраняются на SD даже при потере радио | Fallback | Data logger — core module |
| REQ-SEC-01 | Все телекоманды с HMAC-SHA256 | Threat T1 | `command_dispatcher.c` + key_store |
| REQ-SEC-02 | Защита от replay в окне 64 кадров | Threat T2 | 32-бит counter + sliding bitmap |
| REQ-REL-01 | Reboot-loop guard — не более 5 warm-reset подряд | Reliability | `main.c` + `.noinit` counter |

Полная traceability в [`../../requirements/traceability.csv`](../../requirements/traceability.csv).

---

## 4. Обоснование выбора датчиков

| Датчик | Part # | Зачем именно этот | Альтернативы (отвергнутые) |
|---|---|---|---|
| **SBM-20** | СБМ-20 (СССР/Центроник) | Широко доступна, чувствительность 22 имп·с⁻¹·мкЗв⁻¹·ч, рабочий диапазон 0.014–144 мкЗв/ч — перекрывает весь наземный фон с запасом. Выход — GPIO-импульс, легко подхватывается STM32 EXTI. | **CsI(Tl)+SiPM** — в 3× точнее, но 10× дороже и нужна аналоговая цепь. **J305βγ** — аналог SBM-20, но хуже чувствительность. |
| **MS5611** | TE MS5611-01BA03 | Прецизионный barometric pressure — разрешение 10 см по высоте при разрешении 24 бит. Нужно для **точной привязки каждого SBM-20 счёта к высоте**. | BME280 (есть тоже, но хуже разрешение). |
| **BME280** | Bosch BME280 | Влажность + температура среды — корректирует показания давления и даёт научный контекст. | — |
| **BMI088** | Bosch BMI088 | 6-DOF IMU с ±24 g accel — детекция запуска по пороговому g. | MPU-9250 (на 1U CubeSat), тут BMI088 потому что выше G-range. |
| **LIS3MDL** | ST LIS3MDLTR | Магнитометр — пассивная привязка ориентации во время спуска (подтверждение, что банка не кувыркается). | — |
| **u-blox MAX-M10S** | u-blox MAX-M10S | Multi-GNSS (GPS+Galileo+BeiDou+GLONASS) — точность 1.5 м, время холодного старта ≤ 35 с. Критично для recovery. | NEO-6M — вдвое дешевле, но ±2.5 м и только GPS. |
| **RFM95W LoRa** | HopeRF RFM95W 433 МГц | **ISM-полоса 433 МГц не требует HAM-лицензии** в большинстве стран. SF7BW250 даёт 5.5 кбит/с — достаточно для 10 Hz телеметрии 50-байтовыми пакетами. | CC1125 (используется в CubeSat) — на 437 МГц, требует HAM. APC220 — устарел. |

Ни один датчик в этом BOM не избыточен: каждый решает конкретное требование в таблице §3.

---

## 5. Архитектура

```
┌─────────── SBM-20 GEIGER TUBE ──────────────┐
│ Анод ——[1 МОм]—— +400 В DC-DC повышающий     │
│ Импульс ——[RC дифф.]—— MOSFET(SI2301) —— GPIO│
└──────────────────────────┬───────────────────┘
                           │ EXTI line 0 (rising edge, dead-time 100 μs)
                           ▼
┌─────────────────── STM32F446RE ──────────────────┐
│                                                  │
│  TASK_TELEMETRY (10 Hz)      TASK_SBM20 (event)  │
│  ├─ MS5611 read (baro)       ├─ EXTI callback    │
│  ├─ BMI088 read (IMU)        ├─ counter++        │
│  ├─ LIS3MDL read (mag)       └─ timestamp[k]     │
│  ├─ BME280 read (env)                            │
│  ├─ MAX-M10S parse (GNSS)    TASK_DATA_LOG (5 Hz)│
│  └─ build CCSDS packet       └─ SD card CSV      │
│                                                   │
│  TASK_COMM (RFM95W)          TASK_FDIR (1 Hz)    │
│  ├─ HMAC-SHA256 sign         ├─ 12 fault IDs     │
│  ├─ AX.25 frame (bit-stuff)  ├─ grayscale sev.   │
│  └─ LoRa SPI TX              └─ reboot-loop guard│
│                                                   │
│  TASK_DESCENT (1 Hz)          TASK_SCHEDULER      │
│  ├─ baro peak → apogee                            │
│  ├─ IMU stable → landed       FreeRTOS 6 tasks    │
│  └─ servo SG90 control                            │
└──────────────────────────────────────────────────┘
         │                               │
         │ I²C1 @ 400 kHz                │ SPI1 @ 5 MHz
         │                               │
   ┌─────┴─────┬─────┐              ┌────┴────┐
   MS5611  BME280  LIS3MDL          BMI088  RFM95W
   0x76    0x77    0x1C             CS=PA4   CS=PA5
```

---

## 6. Электрическая схема (упрощённо)

```
                    +3.7 V LiPo 1000 mAh
                          │
                 ┌────────┼────────┐
                 │        │        │
           TPS61200    BME280    SBM-20 HV module (DC-DC → +400 V)
           (boost 5V) │ (I²C)     │
                 │    │           └── анод трубки → RC-диффер. → EXTI
                 ▼    ▼
              STM32F446RE ─── I²C ─── MS5611, LIS3MDL, MAX-M10S
                 │
                 ├── SPI ──► RFM95W LoRa
                 ├── SPI ──► BMI088
                 ├── PWM ──► SG90 servo (парашют)
                 ├── EXTI ── SBM-20 импульсы
                 ├── SDIO ── microSD
                 └── USB ── ground checkout
```

Полный KiCad-проект — см. [issue #7 github](https://github.com/root3315/unisat/issues/7) (в процессе).

---

## 7. Бюджет массы

| Категория | Масса (г) |
|---|---:|
| Structure (Ø68×80 алюминий + 2-layer PCB) | 92 |
| OBC (STM32F446 + microSD) | 4 |
| Power (LiPo 1000 mAh + boost) | 25 |
| Sensors (BMI088 + LIS3MDL + MS5611 + BME280) | 4 |
| GNSS (MAX-M10S + патч-антенна) | 9 |
| Radio (RFM95W + λ/4 антенна) | 4 |
| Descent (SG90 + парашют 300 мм) | 23 |
| Harness + wiring | 2 |
| **SBM-20 модуль (трубка + DC-DC + диффер.)** | **50** |
| Thermal (foam impact pad) | 6 |
| **Запас под доработки** | **281** |
| **Итого** | **500** |

Bare-kit без SBM-20 = 170 г (см. `hardware/bom/by_form_factor/cansat_standard.csv`).
SBM-20 модуль = 50 г (трубка 42 г + DC-DC +400 В 5 г + пассивные цепи 3 г).
**Payload-подсистема радиометра занимает 50 / 500 = 10 % массового бюджета.**

---

## 8. Бюджет энергии

| Нагрузка | Режим | Ток (мА) | Длительность |
|---|---|---:|---|
| STM32F446 @ 180 МГц | Active | 90 | 100 % полёта |
| RFM95W | TX 14 dBm | 120 | 10 % (50 мс / 500 мс) |
| RFM95W | Idle | 5 | 90 % |
| MAX-M10S | Continuous | 20 | 100 % |
| SBM-20 DC-DC (+400 В) | Стандарт | 4 | 100 % |
| BMI088 + LIS3MDL + MS5611 + BME280 | Normal | 3 | 100 % |
| SD card | Write bursts | 30 | 20 % |
| SG90 servo | Idle / move | 8 / 250 | 99 % / 1 % |
| **Среднее потребление** | | **~140 мА** | |

LiPo 1000 мАч × 3.7 В / 0.14 А / 3.7 В = **~7 часов работы**. Миссия < 30 минут → запас 14×. SoC в конце полёта ~95 %.

---

## 9. Бюджет радиолинии

| Параметр | Значение |
|---|---|
| Частота | 433 МГц ISM |
| Модуляция | LoRa SF7 BW 250 kHz |
| TX мощность | +14 dBm (25 мВт) |
| Антенна борт | λ/4 провод, усиление 0 dBi |
| Антенна земля | λ/4 штырь или yagi 5 dBi |
| Дальность расчётная (LoS) | **> 2 км** с yagi |
| Фактический bit rate | 5.5 kbps (SF7BW250) |
| Телеметрия packet | 50 B (AX.25 + CCSDS + HMAC-32 + payload) |
| Cadence | 10 Hz |
| Эфирная нагрузка | 500 B/s ≪ 687 B/s потолок |

Link budget: TX +14 dBm − path loss (2 км @ 433 МГц = −91 dB) − margins −10 dB + RX antenna +5 dBi = **−82 dBm**, при чувствительности RFM95W SF7 = **−124 dBm**. **Margin 42 dB** — с большим запасом.

---

## 10. Test matrix

| ID | Тест | Метод | Критерий успеха |
|---|---|---|---|
| T-01 | Pre-launch mass check | Precision scale ±0.1 г | ≤ 500 г ✓ |
| T-02 | Pre-launch dimension | Штангенциркуль | Ø68 × 80 мм ±0.5 мм |
| T-03 | SBM-20 калибровка на наземном фоне | 10-мин окно, нулевой источник | ~20 имп/мин (естественный фон) |
| T-04 | SBM-20 калибровка на источнике Cs-137 | Известная активность 100 кБк | Относительная ошибка ≤ 15 % |
| T-05 | LoRa range test | Yagi на 2 км от стенда | FER ≤ 10 % |
| T-06 | GNSS cold start | Outdoor, антенна открытая | ≤ 90 с до fix |
| T-07 | Parachute deploy, bench | Servo PWM команда | Освобождение за ≤ 50 мс |
| T-08 | Drop test 30-50 м | Квадрокоптер или воздушный шар | Descent rate 6-11 м/с |
| T-09 | 30-мин battery endurance | LiPo 1000 мАч, all subsystems | SoC > 80 % в конце |
| T-10 | SITL full-flight | `python flight-software/run_cansat.py` | Все фазы пройдены |
| T-11 | FDIR recovery | Snip-off датчика на 5 с | DEGRADED mode, не REBOOT |
| T-12 | Reboot-loop guard | Принудительно 5× reset | 6-й → SAFE mode |

T-01, T-02, T-05, T-06, T-07, T-08, T-09 — **физические**, сигнируются командой на полигоне.
T-10, T-11, T-12 — **SITL** (уже зелёные в CI).
T-03, T-04 — **bench с радиоактивным источником** (требуется для SBM-20-специфичной миссии).

---

## 11. Риски и митигация

| Риск | Вероятность | Impact | Митигация |
|---|---|---|---|
| SBM-20 HV DC-DC не стартует на холоде | Средняя | Нет данных | Pre-launch: 5 мин прогрев от батареи перед пуском |
| GNSS не получает fix под обтекателем | Высокая | Потеря recovery | Fix до запуска, последняя координата в beacon |
| Парашют не раскрывается | Низкая | Разрушение | Дублирование: pyro cutter + servo SG90 (на advanced) |
| Потеря радиоканала | Средняя | Нет телеметрии | On-board CSV на SD (fallback) |
| Магнитное загрязнение от servo | Низкая | Шум LIS3MDL | Сервопривод размещён на противоположном от магнитометра торце |
| Cold start LiPo ниже 0 °C | Высокая в холодный день | Просадка напряжения | Пенопластовый чехол + химическая грелка в обитаемом объёме |

---

## 12. Готовность к запуску

```
[ ] T-01 mass check passed
[ ] T-02 dimension check passed
[ ] T-03 + T-04 SBM-20 calibration recorded
[ ] T-05 radio range ≥ 2 км підтверджено
[ ] T-06 GNSS cold start test
[ ] T-07 parachute servo функционирует
[ ] T-08 drop test с квадрокоптера пройден
[ ] T-09 30-мин battery test пройден
[x] T-10 SITL full-flight (автотест в CI)
[x] T-11 FDIR recovery
[x] T-12 Reboot-loop guard
[ ] Pre-flight GO/NO-GO команда подписана
[ ] SD card formatted + free ≥ 2 GB
[ ] LoRa channel interference check на площадке
[ ] HMAC ключ загружен и подтверждён echo-test
```

`[x]` — подтверждено в `scripts/verify.sh` / pytest CI / `make target-cansat_standard`.
`[ ]` — физические gate, сигнируются командой на полигоне.

---

## 13. Команда и графики

| Роль | Ответственный | Deliverable |
|---|---|---|
| Научный лидер | *[имя]* | §2, анализ данных |
| OBC + firmware | *[имя]* | `firmware/` host build + ARM flash |
| SBM-20 + HV | *[имя]* | DC-DC модуль, калибровка |
| Ground station | *[имя]* | Streamlit + LoRa приёмник |
| Механика | *[имя]* | Корпус Ø68×80, сборка, mass check |
| Презентация | *[имя]* | Слайды, видео, защита |

**Milestones:** устный роадмап с командой (отдельного TIMELINE.md пока нет).

---

## 14. Связь с репозиторием

Все технические решения в этом CDR реализованы в коде:

- Реестр форм-факторов: [`flight-software/core/form_factors.py`](../../../flight-software/core/form_factors.py) → `cansat_standard`
- Mission profile: [`flight-software/core/_profiles/cansat.py`](../../../flight-software/core/_profiles/cansat.py) → `cansat_standard_profile`
- Firmware profile macro: [`firmware/stm32/Core/Inc/mission_profile.h`](../../../firmware/stm32/Core/Inc/mission_profile.h) → `MISSION_PROFILE_CANSAT_STANDARD`
- Build: `make target-cansat_standard`
- SBM-20 driver: [`firmware/stm32/Drivers/SBM20/`](../../../firmware/stm32/Drivers/SBM20/)
- Descent controller: [`payloads/cansat_descent/`](../../../payloads/cansat_descent/)
- BOM: [`hardware/bom/by_form_factor/cansat_standard.csv`](../../../hardware/bom/by_form_factor/cansat_standard.csv)
- Ops guide: [`docs/ops/cansat_standard.md`](../../ops/cansat_standard.md)

---

**Документ подписан:** *[team lead signature]*
**Версия:** 1.0 (2026-04-19)
**Следующая ревизия:** после T-08 drop-теста
