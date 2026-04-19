# UzCanSat 2026 — compliance checklist

Проверка соответствия нашей платформы **официальному регламенту UzCanSat 2026** (источник: [training.cmspace.uz/youth-projects/16](https://training.cmspace.uz/youth-projects/16), оригиналы в [`references/official/`](references/official/)).

**Короткий ответ:** полностью совместимо через preset `mission_templates/cansat_uzcansat.json`. Универсальная архитектура UniSat `cansat_standard` не меняется — UzCanSat-специфика вынесена в **один JSON**.

---

## Регламент оценки (100 баллов) — покрытие

| Критерий | Макс | Где закрыто | Ожидаемая оценка |
|---|---:|---|---:|
| 1. Проектная документация | 15 | [`CDR.md`](CDR.md) + 8 ADRs + traceability CSV | **15** |
| 2. Аппаратный дизайн | 10 | [`hardware/bom/by_form_factor/cansat_standard.csv`](../../../hardware/bom/by_form_factor/cansat_standard.csv) + envelope Ø68×80 в `form_factors.py` | **7** (без физ. сборки) → **10** после drop-теста |
| 3. Программное обеспечение | 10 | 299 pytest + 28 ctest + FDIR + HMAC + grayscale severity | **10** |
| 4. Сбор и передача данных | 20 | Sensors + 1 Hz telemetry + SD CSV + ground PCAP (тройная защита) | **18** после реального полёта |
| 5. Научная миссия | 15 | [`SCIENCE_MISSION.md`](SCIENCE_MISSION.md) — SBM-20 радиационный профиль | **12** |
| 6. Тестовый запуск | 10 | SITL green; drop-test — gate команды | **9** после drop-теста |
| 7. Презентация | 20 | [`PRESENTATION.md`](PRESENTATION.md) 10 слайдов + [`POSTER.md`](POSTER.md) | **18** |
| **Бонус**: доп. датчик (SBM-20) | +5 | [`SCIENCE_MISSION.md`](SCIENCE_MISSION.md) §3 | **+5** |
| **Штраф**: вес > 500 г | −5/10 г | BOM 170 г kit + headroom | 0 |
| **Штраф**: отказ системы | −20 | FDIR + reboot guard + HMAC | 0 риск |
| **Штраф**: нет ключевых данных | −20 | Тройное резервирование в [`KEY_DATA_PACKET.md`](KEY_DATA_PACKET.md) | 0 риск |

**Прогноз при полном выполнении:** **~95/100**. Прогноз сейчас (до сборки): **~46/100**.

---

## Qollanma.pdf §5 — требования к аппарату

| UzCanSat требует | Наша реализация | Файл |
|---|---|---|
| **Корпус ≤ 500 г, Ø68 × 80 мм, Ø64 внутр.** | `cansat_standard` envelope | [`form_factors.py`](../../../flight-software/core/form_factors.py) |
| Алюминиевая банка или 3D-печать | BOM row `Structure,Aluminium can housing,CAN-68x80` | [`cansat_standard.csv`](../../../hardware/bom/by_form_factor/cansat_standard.csv) |
| Отверстия для вентиляции датчиков | Механика команды | *внешнее требование* |
| Лёгкая замена батареи/основных частей | Bolt-on PCB mount на 4×M2 | CDR §6 |
| Температура, давление, влажность | BME280 + MS5611 | BOM |
| GPS | u-blox MAX-M10S | BOM |
| Акселерометр + гироскоп | BMI088 (6-DOF) | BOM |
| **Zummer (для школ)** | **Добавлено в preset** — `subsystems.buzzer.enabled: true` | [`cansat_uzcansat.json`](../../../mission_templates/cansat_uzcansat.json) |
| Батарея LiPo 3.7 В или AA | LiPo 1000 мАч | BOM |
| **Камера горизонтальная, ≥ 640×480, ≥ 30 fps, на SD** | `subsystems.camera` в preset с явными полями | `cansat_uzcansat.json` |
| Видео от запуска до приземления | `record_from: launch_detect, record_until: landed+10s` | `cansat_uzcansat.json` |
| Парашют из нейлона / полиэтилена | BOM row `CHUTE-300` | BOM |
| Парашют не повреждает CanSat | Descent rate 6–11 м/с → < 12 м/с удар | [`descent_controller`](../../../payloads/cansat_descent/) |

---

## Qollanma.pdf §Ma'lumotlarni uzatish — передача данных

| UzCanSat требует | Наша реализация |
|---|---|
| **Телеметрия 1 Hz** (каждую секунду) | `mission.telemetry_hz: 1.0` в preset |
| Передача от запуска до приземления + 10 с | `record_until: landed + 10s` в preset |
| После приземления: зуммер / GNSS | `subsystems.buzzer` + `subsystems.gnss` в preset |
| Дальняя передача без помех | LoRa SF7 @ +14 dBm → margin 42 dB на 2 км (см. CDR §9) |
| Ground station: антенна + компьютер | Streamlit ground-station app + yagi @ 5 dBi |
| Телеметрические графики в реальном времени на ПК | ground-station/pages/02_telemetry.py |

---

## Qollanma.pdf §4.2 — бонусные задачи (extra points)

| Задание | Решено в | Как включается |
|---|---|---|
| **Алгоритм высоты из баро в реальном времени** | `flight-software/modules/barometric_altimeter.py` (существует) | `features.realtime_altitude: true` |
| **Мгновенная скорость из acc + gyro** | Integration of BMI088 output | `features.instantaneous_velocity: true` (включено в preset) |

Обе функции **включены по умолчанию** в `cansat_uzcansat.json` → команда получает бонусные очки «бесплатно» для выбранных судьями задач.

---

## Что НЕ менялось в ядре платформы

- `flight-software/core/form_factors.py` — без изменений (envelope и так правильный)
- `flight-software/core/_profiles/cansat.py` — без изменений (`cansat_standard_profile` остаётся generic 10 Hz)
- `hardware/bom/by_form_factor/cansat_standard.csv` — без изменений (эталонный BOM для ЛЮБОЙ CanSat-команды)
- `firmware/stm32/Drivers/*/` — без изменений (buzzer — один GPIO, не нужен новый драйвер)
- `docs/ops/cansat_standard.md` — без изменений (generic ops-гайд не UzCanSat-специфичный)

**UzCanSat-preset это надстройка, не fork.** Если появится ESERO-CanSat с другими требованиями — будет `cansat_esero.json`, не ветка кода.

---

## Активация preset

```bash
# 1. Выбираем UzCanSat preset вместо generic standard
cp mission_templates/cansat_uzcansat.json mission_config.json

# 2. Всё остальное — как в стандартном UniSat workflow:
make target-cansat_standard      # firmware (тот же, preset оверрайдит только конфиг)
cd flight-software && python flight_controller.py
cd ground-station && streamlit run app.py
```

Flight controller прочтёт `mission_config.json`, увидит `telemetry_hz: 1.0`, `features.buzzer: true` и сам настроится под UzCanSat — **без перекомпиляции firmware**.

---

## Официальные документы

Все 6 файлов с cmspace.uz (скачано 2026-04-19) приложены в [`references/official/`](references/official/):

| Файл | Язык | Что |
|---|---|---|
| `Reglament_ocenki_RU.docx` | рус. | Регламент оценки — 100 баллов |
| `Baholash_Reglamenti_UZ.docx` | узб. | То же, узбекская версия |
| `Plan_meropriyatiya_CanSat_RU.docx` | рус. | Программа конкурса |
| `Tatbir_rejasi_CanSat_UZ.docx` | узб. | То же, узбекская версия |
| `Qollanma.pdf` | узб. | Техническое руководство (13 страниц) — **главный документ** |
| `CanSat_olchamlari.png` | — | Официальная схема размеров Ø68 × 80 / Ø64 / 500 г |

При любом конфликте регламента с preset — победа за официальным документом. Обновлять `cansat_uzcansat.json` через PR.

---

## Цепочка ответственности

| Нужно | Кто реализует |
|---|---|
| JSON preset | **UniSat платформа** (этот файл) |
| Physical hardware build | **Команда** |
| Drop-test + полёт | **Команда** |
| Science payload и его обоснование | **Команда** (можно взять наш SBM-20 mission pack или свой) |
| Калибровка перед полётом | **Команда** |
| Post-flight анализ | `scripts/analyze_cansat_radiation.py` + ручная интерпретация |
