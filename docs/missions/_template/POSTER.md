# POSTER — <Mission name>

A0 portrait poster (841 × 1189 mm). Source layout in ASCII below; render with
your preferred typesetting tool (LaTeX `tikzposter`, Marp, or SVG).

## ASCII layout

```
+----------------------------------------------------------+
|  TITLE: <mission name> — one-line subtitle               |
|  TEAM: name · institution · contact                      |
+----------------------------------------------------------+
|  ABSTRACT                                                 |
|  3-4 sentences. Question, method, result.                 |
+--------------------------+--------------------------------+
|  SCIENCE QUESTION        |  CONOPS                        |
|  H0 / H1 / decision rule |  ASCII flow diagram            |
+--------------------------+--------------------------------+
|  PAYLOAD                 |  KEY DATA                      |
|  Sensor table            |  Beacon format + sample row    |
+--------------------------+--------------------------------+
|  SUBSYSTEMS              |  VERIFICATION                  |
|  Block diagram           |  Test → REQ traceability       |
+--------------------------+--------------------------------+
|  RESULTS / EXPECTED RESULTS                                |
|  Plot, plot, plot. The poster's most-read square.         |
+----------------------------------------------------------+
|  REPOSITORY: github.com/root3315/unisat                  |
|  LICENCE: Apache 2.0   ·   QR CODE        ·   v1.x.y     |
+----------------------------------------------------------+
```

## Typesetting notes

- Top stripe: project banner. Use the same hero image as `README.md` if there
  is one.
- Body grid: 2 columns × 4 rows fills the page well at 12 pt body / 24 pt headers.
- Bottom stripe: keep the QR code under 80 × 80 mm so it scans from 1.5 m.
- Avoid screenshots of code. Use renderings of plots from the analysis script.
