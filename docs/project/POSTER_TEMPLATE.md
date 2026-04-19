# UniSat Competition Poster Template

Use this template to create an A0/A1 poster for aerospace competitions.

---

## Layout (A0 Portrait: 841 × 1189 mm)

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   🛰️  UniSat — Universal Modular CubeSat Platform      │
│   Team Name | University | Competition Name | Date      │
│                                                         │
├──────────────────────┬──────────────────────────────────┤
│                      │                                  │
│   MISSION OVERVIEW   │   SYSTEM ARCHITECTURE            │
│                      │                                  │
│   • Objectives       │   [Block Diagram SVG]            │
│   • Orbit: 550km SSO │                                  │
│   • Form: 3U CubeSat │   OBC ←UART→ Flight Controller  │
│   • Mass: 2.84 kg    │   ↕ I2C/SPI    ↕ asyncio        │
│   • Lifetime: 2 yr   │   Sensors       Camera + Orbit   │
│                      │                                  │
├──────────────────────┼──────────────────────────────────┤
│                      │                                  │
│   SUBSYSTEMS         │   SIMULATION RESULTS             │
│                      │                                  │
│   ┌────┐ ┌────┐     │   [Power Budget Chart]           │
│   │ADCS│ │EPS │     │   Solar: 5.1W avg                │
│   └────┘ └────┘     │   Consumption: 2.6W nominal      │
│   ┌────┐ ┌────┐     │   Battery: 30Wh, SOC > 60%      │
│   │COMM│ │GNSS│     │                                  │
│   └────┘ └────┘     │   [Thermal Analysis Chart]       │
│   ┌────┐ ┌────┐     │   Internal: -10°C to +40°C      │
│   │CAM │ │PAY │     │                                  │
│   └────┘ └────┘     │   [Link Budget Table]            │
│                      │   UHF: 13.8 dB margin           │
│                      │   S-band: 19.4 dB margin        │
│                      │                                  │
├──────────────────────┼──────────────────────────────────┤
│                      │                                  │
│   GROUND STATION     │   KEY INNOVATIONS                │
│                      │                                  │
│   [Screenshot of     │   1. Modular payload interface   │
│    Streamlit          │      (5 swappable modules)      │
│    Dashboard]         │                                  │
│                      │   2. CCSDS-standard telemetry    │
│   • 10-page web UI   │      with HMAC-SHA256 auth      │
│   • Real-time TM     │                                  │
│   • 3D orbit viz     │   3. Web-based configurator     │
│   • HMAC auth cmds   │      with budget validation     │
│                      │                                  │
│                      │   4. Competition adaptation      │
│                      │      guide (5 formats)           │
│                      │                                  │
├──────────────────────┴──────────────────────────────────┤
│                                                         │
│   RESULTS & CONCLUSIONS                                 │
│                                                         │
│   • 190+ source files, 21,000+ lines of code           │
│   • Full CDR-level documentation (12 documents)        │
│   • Automated CI/CD with GitHub Actions                │
│   • Positive energy balance confirmed by simulation    │
│   • All subsystems tested (unit + integration)         │
│   • Open source: github.com/root3315/unisat            │
│                                                         │
│   Contact: team@example.com | github.com/root3315      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Content Guide

### Title Section
- Project name: **UniSat — Universal Modular CubeSat Platform**
- Team name, university/organization
- Competition name and date
- Logos (team, university, sponsors)

### Recommended Visuals
1. System block diagram (`docs/diagrams/system_block_diagram.svg`)
2. Ground station screenshot (run Streamlit, take screenshot)
3. Power budget chart (from `simulation/visualize.py`)
4. Orbit ground track (from ground station orbit tracker page)
5. 3D CubeSat render (if available from mechanical CAD)
6. Photo of hardware prototype (if built)

### Key Numbers to Highlight
| Metric | Value |
|--------|-------|
| Source files | 190+ |
| Lines of code | 21,000+ |
| Documentation pages | 12 CDR-level |
| Test cases | 80+ |
| Payload modules | 7 (swappable) |
| Ground station pages | 10 |
| Supported form factors | 1U, 2U, 3U, 6U |
| Competitions supported | 5+ types |

### Color Scheme (Space Theme)
- Background: `#0E1117` (dark space)
- Primary: `#4ECDC4` (teal)
- Accent: `#FF6B6B` (coral)
- Text: `#FFFFFF` (white)
- Secondary: `#74B9FF` (light blue)

### Fonts
- Title: Inter Bold or Montserrat Bold, 72pt
- Section headers: Inter SemiBold, 36pt
- Body text: Inter Regular, 18pt
- Code/technical: JetBrains Mono, 14pt

### Tools for Creating the Poster
- **Figma** (recommended) — free, collaborative
- **Canva** — quick templates
- **LaTeX + tikzposter** — academic conferences
- **PowerPoint** — simple but effective
