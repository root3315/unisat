# CanSat «РадиоПрофиль-1» — полный пакет документов миссии

Конкретная CanSat-миссия на платформе UniSat `cansat_standard`: измерение вертикального профиля гамма-радиации 0–500 м с разрешением 80 м на базе датчика SBM-20.

Этот пакет закрывает **4 регламентные слабости** из CanSat-оценки и соответствует **официальному регламенту UzCanSat 2026**:

| Было | Стало |
|---|---|
| Generic template, нет CDR под конкретный аппарат | [`CDR.md`](CDR.md) — 14 разделов, 12 тестов, REQ-traceability |
| Научная миссия 5/15 — «собираем телеметрию» | [`SCIENCE_MISSION.md`](SCIENCE_MISSION.md) — H₀/H₁, обоснование SBM-20 на 5 критериях |
| Презентация 12/20 — нет слайдов | [`PRESENTATION.md`](PRESENTATION.md) (10 слайдов Marp) + [`POSTER.md`](POSTER.md) (A0) |
| Риск −20 за «ключевые данные» | [`KEY_DATA_PACKET.md`](KEY_DATA_PACKET.md) — тройное резервирование + [`baseline_sitl_dataset.csv`](baseline_sitl_dataset.csv) |
| Соответствие конкретному конкурсу (UzCanSat) | [`UZCANSAT_COMPLIANCE.md`](UZCANSAT_COMPLIANCE.md) + preset `mission_templates/cansat_uzcansat.json` |

## Карта документов

```
docs/missions/cansat_radiation/
├── README.md                   ← ты здесь
├── CDR.md                      ← Critical Design Review (14 разделов)
├── SCIENCE_MISSION.md          ← H₀/H₁, обоснование датчиков, метод
├── KEY_DATA_PACKET.md          ← формат ключевых данных + fallback-план
├── PRESENTATION.md             ← 10 слайдов (Marp), talking points в комментариях
├── POSTER.md                   ← ASCII-layout постера A0 + указания по вёрстке
├── UZCANSAT_COMPLIANCE.md      ← чек-лист соответствия регламенту cmspace.uz
├── baseline_sitl_dataset.csv   ← эталонный SITL-полёт (743 строки, 59 SBM-20 событий)
└── references/official/        ← 6 официальных файлов с cmspace.uz (read-only)
    ├── Reglament_ocenki_RU.docx
    ├── Baholash_Reglamenti_UZ.docx
    ├── Plan_meropriyatiya_CanSat_RU.docx
    ├── Tatbir_rejasi_CanSat_UZ.docx
    ├── Qollanma.pdf
    └── CanSat_olchamlari.png
```

UzCanSat-preset лежит **снаружи** этой папки — в [`mission_templates/cansat_uzcansat.json`](../../../mission_templates/cansat_uzcansat.json) — чтобы оставаться в каноническом месте для mission templates.

## Связанные инструменты

- [`scripts/analyze_cansat_radiation.py`](../../../scripts/analyze_cansat_radiation.py) — пост-обработка полётного CSV в radiation profile с аномалиями
- [`tools/playground.py`](../../../tools/playground.py) — Streamlit-лаба, tab «🚀 CanSat SITL» рисует полёт в живую
- [`flight-software/run_cansat.py`](../../../flight-software/run_cansat.py) — полный SITL-запуск с driver-уровневой симуляцией

## Как проверить весь pipeline до полёта

```bash
# 1. Сгенерировать радиационный профиль из эталонного SITL-датасета
python scripts/analyze_cansat_radiation.py \
    docs/missions/cansat_radiation/baseline_sitl_dataset.csv \
    --output data/radiation_profile_baseline.csv

# 2. Посмотреть только аномалии
python scripts/analyze_cansat_radiation.py \
    docs/missions/cansat_radiation/baseline_sitl_dataset.csv \
    --anomalies-only

# Ожидаемый результат:
# [summary] 25 altitude bins · N anomalies (|z|>2) · peak X.XXX μSv/h at Y m (z=Z.Z)
```

Pipeline уже проверен: **находит аномалию 310 м, куда была инжектирована пик +0.08 μSv/h в SITL**.

## Как использовать для защиты на конкурсе

### Перед защитой
1. Прочитать [`CDR.md`](CDR.md) — 14 разделов, это твой основной документ
2. Адаптировать [`PRESENTATION.md`](PRESENTATION.md) под имена команды / институт / даты
3. Сверстать [`POSTER.md`](POSTER.md) в Figma / InkScape на размер A0 + отпечатать

### Во время защиты
1. 10 слайдов = 10-15 минут доклада (talking points в Markdown-комментариях)
2. Если полёта не было — показать [`baseline_sitl_dataset.csv`](baseline_sitl_dataset.csv) + графики из analyze_cansat_radiation.py как **доказательство что pipeline готов**
3. Если полёт был — заменить baseline на реальный CSV, запустить тот же скрипт, получить новый radiation profile

### После защиты
4. Опубликовать реальные данные в `docs/characterization/flight/cansat_YYYYMMDD.csv`
5. Cross-link в [`README.md`](README.md) + обновить CDR §12 (готовность к запуску)

## Тестирование

Все утверждения в документах проверены:

- [x] `scripts/analyze_cansat_radiation.py` запускается на `baseline_sitl_dataset.csv`, находит аномалию на 310 м
- [x] Все markdown-ссылки resolve (проверено автоматическим резолвером)
- [x] BOM + mass budget сходятся (170 г kit + 50 г SBM-20 + 280 г payload headroom = 500 г)
- [x] SBM-20 драйвер существует в [`firmware/stm32/Drivers/SBM20/`](../../../firmware/stm32/Drivers/SBM20/)
- [x] cansat_standard профиль зарегистрирован в [`form_factors.py`](../../../flight-software/core/form_factors.py)

## Версия

v1.5.0 (2026-04-19) — полный CanSat mission pack.

Документы предполагают UniSat v1.4.3 как базовую платформу. При смене версии — сверь:
- API `form_factors.get_form_factor('cansat_standard')` — должен вернуть envelope Ø68×80, 500 г
- `make target-cansat_standard` — должен производить `firmware/build-arm-cansat_standard/unisat_firmware.elf`
- `docs/ops/cansat_standard.md` — не должен противоречить CDR.md
