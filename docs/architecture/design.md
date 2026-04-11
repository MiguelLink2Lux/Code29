# Design — Source & Decisions

## Source of Truth

The UI design lives in **Google Stitch**, accessible via the `stitch` MCP server.

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| Project name | `code29_web`                                         |
| Project ID   | `projects/3663672842421799446`                       |
| MCP endpoint | `https://stitch.googleapis.com/mcp`                  |
| Device type  | Desktop                                              |
| Screens      | ~31 screen instances                                 |
| Last updated | 2026-04-10                                           |

Design log screen: `projects/3663672842421799446/screens/f9ad7757441b47959c5789663b14d913`

To read screens or design context, use the `mcp__stitch__*` tools (e.g. `get_screen`, `list_screens`).

---

## Design Log — CODE29 v1.0

### 1. Brand Identity & Creative Concept

- **Project name:** CODE29
- **Creative North Star:** "The Neon Architect"
- **Personality:** Professional, technical, visionary, and slightly disruptive. Avoids "gamer" tropes in favor of **80s ethical hacking** and **high-performance computing** aesthetics.
- **Value proposition:** The convergence between strategic leadership (CTO) and advanced technical execution powered by AI.

---

### 2. Design System (Neon Architect)

**Color palette:**
- Base: Deep blacks and charcoal greys (`#131314`) for maximum contrast.
- Accent: Neon cyan (`#00F0FF`) used for CTAs and critical data elements.

**Typography:**
- Primary: *Space Grotesk* — a geometric sans-serif that evokes technology and clarity.
- Support: *Monospaced* styles for technical data and logs, reinforcing terminal aesthetics.

**Iconography:** Minimalist, thin-line, with subtle outer glow effects to simulate phosphor screens.

---

### 3. UX Decisions & Structure (Master Landing)

Single Page Application style — unified scroll experience to improve retention and information flow.

1. **Hero Section (The Singularity):** Immediate impact with the CTO vision and real photography integrated into a futuristic server environment.
2. **Core Stats:** Visualization of impact metrics (Speed, Efficiency, Scalability, Security) to make AI value tangible.
3. **Education & Stack:** Section dedicated to the AI Master's degree and key tools, positioning as an updated expert.
4. **What I Do (Services):** Replaces traditional portfolio with modular service blocks (CTO as a Service, AI Project Manager) — oriented toward consulting and leadership.
5. **Social Proof (Testimonials):** Testimonials for immediate trust building.
6. **Contact (Direct Uplink):** Terminal-aesthetic form to close the conversion cycle.

---

### 4. Content Strategy (AI-First)

- **Language:** Spanish (localized for target market).
- **Tone:** Direct, expert, results-oriented.
- **AI integration:** Treated not as an external tool but as the central engine of development and project organization at CODE29.

---

### 5. Suggested Next Steps

- Optimize specific copy in the testimonials section.
- Expand "Synapse Records" (Blog) with technical articles.
- Implement subtle "glitch" animations or data flow effects to reinforce interactivity.

---

## Design System — Token Reference

| Role                      | Token                    | Hex       |
|---------------------------|--------------------------|-----------|
| Surface base              | `surface`                | `#131314` |
| Secondary content         | `surface-container-low`  | `#1C1B1C` |
| Interactive cards         | `surface-container-high` | `#2A2A2B` |
| Overlays / Modals         | `surface-bright`         | `#3A393A` |
| Primary accent (cyan)     | `primary`                | `#00F0FF` |
| Secondary accent (violet) | `secondary-container`    | `#9D00FF` |
| On-surface text           | `on-surface`             | `#E5E2E3` |
| Outline / ghost border    | `outline-variant`        | `#3B494B` |

### Typography

| Role              | Typeface      | Notes                                    |
|-------------------|---------------|------------------------------------------|
| Display/Headlines | Space Grotesk | Wide apertures, geometric, authoritative |
| Body/Titles       | Manrope       | Clean sans-serif, legible long-form      |
| Labels/Data       | Space Grotesk | Monospace, uppercase, +5% letter-spacing |

---

## Non-Negotiable Design Rules

### Border Radius
**0px always.** Rounded corners are strictly forbidden.

### No 1px Borders
Boundaries defined through background color shifts only — never solid lines.

### Glassmorphism (floating elements)
- Background: `surface-variant` at 60% opacity
- Filter: `backdrop-filter: blur(24px)`

### Ambient Shadows
```css
box-shadow: 0px 20px 40px rgba(0, 219, 233, 0.08);
```

### Buttons — Primary
Gradient from `#DBFCFF` to `#00F0FF` at 45°. On hover: 4px outer glow.

### Input Fields
Underline-only (2px `outline-variant`). On focus: transitions to `primary` with 2px blur glow.
