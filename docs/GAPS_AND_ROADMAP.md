# UniSat — Gaps & Roadmap

**Честный статус на апрель 2026.** Что работает зелёным, что
остаётся делать, что принципиально вне scope'а.

---

## Верификация на сегодня

| Проверка | Статус |
|---|---|
| Host build firmware (`unisat_core`) | ✅ clean |
| C unit tests (`ctest`) | ✅ **16 / 16** |
| Python tests (`pytest`, ground-station) | ✅ **34 / 34** |
| Hypothesis property + fuzz | ✅ 200 + 500 cases |
| AX.25 golden vectors C↔Python | ✅ 28 / 28 byte-identical |
| SHA-256 FIPS 180-4 vectors | ✅ |
| HMAC-SHA256 RFC 4231 vectors | ✅ |
| End-to-end SITL beacon demo | ✅ `./scripts/verify.sh` |
| Threat T1 (command injection) | ✅ mitigated by HMAC dispatcher |
| Threat T3 (bit-stuff DoS) | ✅ hard-reject >400 B |
| Threat T4 (RF garbage flood) | ✅ decoder never crashes (fuzz) |

**Сегодня платформа готова к подаче на любой студенческий /
университетский конкурс.**

---

## Что ещё можно добавить (приоритизировано)

### 🟡 Medium priority — ощутимые улучшения

#### M1. T2 replay protection (оставшаяся часть Track 1b)

**Что:** команды с валидным HMAC, но старым timestamp'ом или
повторным sequence-number'ом отклонять.

**Как:** в `command_dispatcher.c` добавить проверку CCSDS
secondary-header (timestamp + seq) против sliding window (последние
16 принятых sequence numbers + freshness ±60 сек).

**Оценка:** ~2 часа. Низкий риск.

**Impact:** закрывает последнюю серьёзную security-дыру.

---

#### M2. Streamlit ↔ AX.25 live bridge

**Что:** Streamlit dashboard читает **реальные** beacon'ы, не demo
данные из SQLite.

**Как:** добавить фоновый воркер в `ground-station/app.py`, который
слушает `ax25_listen.py` по TCP и пишет декодированные frame'ы в
ту же SQLite, которую читает UI.

**Оценка:** ~3 часа.

**Impact:** демо становится эффектнее — видно реальные пакеты в
UI, не статичные примеры.

---

#### M3. Flight-software end-to-end scenario test

**Что:** один большой тест "полная миссия" от LEOP → detumble →
nominal → imaging → downlink → safe mode. Сейчас есть 14 unit-
тестов модулей, но нет integration-сценария.

**Как:** `flight-software/tests/test_full_mission.py` с asyncio
event loop, имитирующим 24 часа виртуального полёта за 10 секунд
реальных.

**Оценка:** ~4 часа.

**Impact:** уверенность, что модули корректно взаимодействуют во
всех фазах миссии.

---

### 🟢 Low priority — nice-to-have

#### L1. Real radio modulation config (CC1125)

**Что:** документ + пример регистровых настроек для CC1125 (UHF
радио из BOM): GFSK 9600 bps, RF 437 MHz, deviation 2.4 kHz.

**Оценка:** ~1 час чтения datasheet + 100 строк config dumps.

**Impact:** кто-то, собирающий реальное железо, не тратит день на
поиск настроек в datasheet.

---

#### L2. Regulatory / licensing info

**Что:** раздел в README или отдельный `docs/REGULATORY.md` —
как получить amateur radio callsign, как подать заявку на IARU
frequency coordination, какие страны требуют что.

**Оценка:** ~2 часа research'а.

**Impact:** полезно для команд, которые планируют **реальный**
запуск. Для учебных конкурсов не нужно.

---

#### L3. Commissioning / operational runbook

**Что:** пошаговая инструкция на день запуска и первые 72 часа:
acquire signal → first beacon → detumble check → deploy panels →
first image → TT&C schedule.

**Оценка:** ~3 часа.

**Impact:** опять же, только для реального запуска.

---

#### L4. Hardware-in-the-loop testbed

**Что:** скрипт, который принимает настоящий STM32F446 через
USB-UART и имитирует orbit/sensor данные в реальном времени
(Renode или самописный bridge).

**Оценка:** 1–2 недели работы.

**Impact:** максимальный для TRL uplift. Но это уже серьёзный
инженерный труд, не вечерняя задача.

---

### ⚪ Out of scope — принципиально вне платформы

#### X1. Flight heritage

Никакое ПО не заменит реальный запуск на орбиту и возврат
невредимым. Для flight heritage нужен либо CubeSat на чьей-то
попутке (CSLI, Dispenser), либо лабораторная квалификация (TID,
TVT, Vibration, EMC) стоимостью десятки тысяч долларов.

Проект сам по себе **не даёт** flight heritage — это ПО основа
для команды, которая уже имеет доступ к железу и запуску.

#### X2. Radiation hardening

Soft-error mitigation (ECC-RAM, TMR, watchdog scrubbing) требует
либо rad-hard MCU (стоимость ~$50K), либо детального радиационного
тестирования (cyclotron time). Platform предоставляет базовые
fault-tolerance примитивы (watchdog, safe mode, error handler с
EEPROM persistence), но настоящая radiation tolerance — отдельная
инженерная дисциплина.

#### X3. Certified mission assurance (NASA-STD-8739.x, ECSS-Q-ST-40)

Формальная mission assurance документация для NASA/ESA-class
миссий — десятки документов, процессов, reviews. Платформа
**не претендует** на этот уровень. Она ориентирована на
educational / research / amateur-launch сегмент.

---

## Roadmap по версиям

### v1.1 (текущая, апрель 2026)

✅ Полный AX.25 link layer
✅ HMAC-SHA256 command dispatcher
✅ End-to-end SITL demo
✅ 50/50 тестов зелёные
✅ CDR-level документация

### v1.2 (planned)

- [ ] M1 — replay protection
- [ ] M2 — Streamlit live bridge
- [ ] M3 — flight-software e2e scenario
- [ ] L1 — CC1125 radio config doc

### v1.5 (stretch)

- [ ] L3 — commissioning runbook
- [ ] L4 — HIL testbed prototype
- [ ] Real orbital test partnership / CSLI proposal

---

## Как помочь

См. `CONTRIBUTING.md`. Приоритетно ждём M1/M2/M3 — любая из
этих задач делает платформу заметно лучше и умещается в одну-две
вечерних сессии.

---

*Last updated: 2026-04-17*
