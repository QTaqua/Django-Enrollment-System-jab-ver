# Holy Trinity University — Brand Reference

Reference package for the **Holy Trinity University · Enrollment System** user
interface. It separates verified institutional facts from design choices made
for this application.

- Repository identity: **ADS Enrollment System** (academic project).
- Interface identity: **Holy Trinity University · Enrollment System**.
- Official website: <https://www.htu.edu.ph/>
- Reference retrieved: **2026-11-01**
- Scope: identification and visual consistency for a non-commercial academic
  project. This document is not an official HTU brand guide.

> **Disclaimer**
>
> Official Holy Trinity University institutional marks are reproduced unmodified
> for identification in a non-commercial academic project. This project is
> independently developed for educational demonstration and is not an official
> HTU publication or university-operated service. All institutional marks remain
> the property of their respective owner.

---

## 1. Institutional identity

| Item | Value | Status |
| --- | --- | --- |
| Official name | Holy Trinity University | **Official and verified** (htu.edu.ph) |
| Abbreviation | HTU | **Official and verified** (htu.edu.ph) |
| Type | Private sectarian university run by the Dominican Sisters of Saint Catherine of Siena | **Official and verified** (htu.edu.ph homepage) |
| Main campus | Quezon Street, Brgy. Maligaya, Puerto Princesa City, Palawan, Philippines | **Official and verified** (contact directory) |
| Other campuses | Sta. Monica; Tiniguiban | **Official and verified** (contact directory) |
| Contact | htu.palawan@htu.edu.ph · (048) 433 2161 | **Official and verified** (contact directory) |
| Student demonym | Trinitian | **Official and verified** (htu.edu.ph) |
| Footer tagline | “The first dynamic center of Catholic Education in Palawan.” | **Official and verified** (site footer) |

Official description published on the homepage:

> “Holy Trinity University is a private sectarian university in Puerto Princesa
> City in the province of Palawan, run by the Dominican Sisters of Saint
> Catherine of Siena. Holy Trinity University is a dynamic center of Catholic
> education in Palawan, Philippines.”

## 2. Vision and mission

**Vision** — <https://www.htu.edu.ph/vision-and-mission/>

> Holy Trinity University, a dynamic agent in the evangelizing mission of the
> Catholic Church, envisions to become glocally innovative and resilient to the
> challenges of the 21st century in the spirit of synodality.

**Mission** — same page

> HTU INSTILLS, NURTURES, and LIVES the values of Passion for Truth and
> Compassion for Humanity, exemplified by Venerable Mo. Francisca del Espiritu
> Santo de Fuentes, for the integral formation of persons for service and
> leadership in transforming society.

**Objectives** — same page

1. To strengthen the integration of the Gospel values lived by Ven. M. Francisca
   del Espiritu Santo de Fuentes in all aspects of school operation.
2. To intensify transformative OP-Siena education that fosters innovative,
   relevant, resilient, sustainable, and holistic programs and empowers
   stakeholders in the spirit of communion, participation and mission.
3. To respond to the challenges of the 21st century digital world and to foster
   the development of the educational research and Palawan studies.
4. To institutionalize the community engagement and collaborative partnership
   with different agencies.

**Motto:** no official motto is published on htu.edu.ph. Third-party sources
mention *“In Servitudine Veritatis”*; treat that as **not yet verified** and do
not display it as official.

## 3. Institutional history (verified highlights)

Source: <https://www.htu.edu.ph/history/>

- **1940** — Holy Trinity Academy founded; pioneer higher-learning institution
  in Palawan.
- **1950** — becomes a Junior College.
- **1953** — renamed Holy Trinity College.
- **1963–1995** — expansion: St. Dominic Building (1963), Pre-Nursing and
  Graduate School (1965), St. Catherine Building (1984–1985), BS Nursing (1987),
  Palawan Environmental Research Center (1990–1991).
- **23 December 2009** — CHED grants university status; Holy Trinity University.
- **2015** — 75th anniversary; **2025** — 85th anniversary.
- **2024–2025** — historic acacia named “Trinicacia”; PNLE Top-5 national
  performance; sixth university president installed June 2025.
- Heritage: founded and run by the **Dominican Sisters of Saint Catherine of
  Siena** (Siena Sisters); the mission names **Venerable Mother Francisca del
  Espiritu Santo de Fuentes**.

---

## 4. Official seal and assets

All assets below are hosted by the official HTU website and are used
**unmodified**. Files are bundled under `static/img/` so the interface does not
depend on hotlinking.

| Purpose | Repository file | Official source URL | Format | Dimensions | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| Primary seal | `static/img/htu-seal.png` | `https://www.htu.edu.ph/wp-content/uploads/2025/10/htulogo.png` | PNG, 32-bit ARGB, transparent | 319 × 320 | `593baf59326dbec4a2ae82a19b6b16631e2991d7292a6b6fe1c7f6255a6b157a` |
| Favicon 32 | `static/img/favicon-32x32.png` | `.../2025/10/cropped-htulogo-32x32.png` | PNG | 32 × 32 | `bc8eae7b1b1578f2895f36ab691e4a93616d4de0c454a32d7af5fbfe5cd31dc0` |
| Favicon 192 | `static/img/favicon-192x192.png` | `.../2025/10/cropped-htulogo-192x192.png` | PNG | 192 × 192 | `38d51bb913f3bddefbb116dbaa5923f26b3c9298d5065c0be06a6ef584e92273` |
| Apple touch icon | `static/img/apple-touch-icon-180x180.png` | `.../2025/10/cropped-htulogo-180x180.png` | PNG | 180 × 180 | `92a60308ec8d293dadb2b36d4dc368e4430bc7aaae7b8c3e8b50237f32e0999b` |

The seal is referenced by the official site header and footer with
`alt="Official Logo of Holy Trinity University"` and is registered in the site
media library (ID 78). Square variants are derived by the university itself for
site-icon use.

**Seal structure (observed, no official meaning documented):** circular seal with
an outer inscription ring, a solid dark-green inner field, and a red-and-gold
central emblem with black line work.

**Asset rules**

- Do not redraw, recolour, crop, distort, stretch, or replace the seal.
- Preserve transparency and the 319:320 proportion.
- Do not use the seal as a low-contrast background or watermark behind text.
- Do not place the seal on busy photography.
- Decorative repeats beside the university wordmark use `alt=""`; a standalone
  seal uses an explicit alternative text such as “Holy Trinity University seal”.

---

## 5. Colour system

### 5.1 Verified official website colours

Extracted from the live site's Elementor kit stylesheet
(`/wp-content/uploads/elementor/css/post-80.css`) and its inline theme CSS.

| Value | Use on htu.edu.ph | Status |
| --- | --- | --- |
| `#324A6D` | Global text colour (navy) | **Official and verified** (website CSS) |
| `#FFBE00` | Global accent (gold) | **Official and verified** (website CSS) |
| `#F3F5F8` | Secondary background | **Official and verified** (website CSS) |
| `#F9FAFD` | Paper / light surface | **Official and verified** (website CSS) |
| `#C8D5DC` | Border / mist | **Official and verified** (website CSS) |
| `#FFFFFF` | Base surface | **Official and verified** (website CSS) |
| `#000000` | Headings | **Official and verified** (website CSS) |

These are **website design tokens**, not a published institutional brand
standard.

### 5.2 Colours sampled from the official seal

Sampled from opaque pixels of `htulogo.png` (2-pixel grid, exact-colour
histogram). These are **sampled approximations**, not official brand values.

| Value | Observed share of opaque pixels | Status |
| --- | --- | --- |
| `#43783A` (green, with near shades) | ≈ 8 % combined | **Sampled approximation** |
| `#A81F23` (red) | 1.6 % | **Sampled approximation** |
| `#F8D30C` (gold) | 1.1 % | **Sampled approximation** |
| `#FFFFFF`, `#000000` | 34.7 %, 6.5 % | Neutral artwork |

Third-party sources describe HTU colours as “red and gold”. That claim is
**not yet verified** against an official HTU source.

### 5.3 Application palette (proposed)

Defined in `static/css/htu-theme.css`.

| Token | Value | Role | Status |
| --- | --- | --- | --- |
| `--htu-green` | `#43783A` | Brand anchor, secondary surfaces | **Sampled approximation** |
| `--htu-green-deep` | `#2F5B2B` | Header, footer, primary actions | **Proposed design interpretation** (darker shade of the sampled green) |
| `--htu-green-darker` | `#24471F` | Hover/active state | **Proposed design interpretation** |
| `--htu-gold` | `#FFBE00` | Accent rule, focus ring, highlights | **Official and verified** (website accent) |
| `--htu-gold-soft` | `#FFF6CC` | Highlight wash | **Proposed design interpretation** |
| `--htu-seal-gold` | `#F8D30C` | Reference only; never text colour | **Sampled approximation** |
| `--htu-red` | `#A81F23` | Destructive/error accent | **Sampled approximation** |
| `--htu-navy` | `#324A6D` | Secondary headings and table heads | **Official and verified** (website text colour) |
| `--htu-surface` | `#F3F5F8` | Page background | **Official and verified** (website token) |
| `--htu-paper` | `#F9FAFD` | Table head tint | **Official and verified** (website token) |
| `--htu-mist` | `#C8D5DC` | Borders and dividers | **Official and verified** (website token) |
| `--htu-ink` | `#1F2328` | Body text | **Proposed design interpretation** |
| `--htu-muted` | `#5B6670` | Secondary text | **Proposed design interpretation** |

**Contrast checks (WCAG 2.1, computed):**

| Pair | Ratio | Result |
| --- | --- | --- |
| `#2F5B2B` on `#FFFFFF` | 7.92:1 | AAA normal text |
| `#43783A` on `#FFFFFF` | 5.27:1 | AA normal text |
| `#A81F23` on `#FFFFFF` | 7.28:1 | AAA |
| `#324A6D` on `#FFFFFF` | 8.99:1 | AAA |
| `#5B6670` on `#FFFFFF` | 5.87:1 | AA |
| `#1F2328` on `#FFBE00` | 9.49:1 | AAA |
| `#1F2328` on `#F8D30C` | 11.86:1 | AAA |
| `#FFFFFF` on `#FFBE00` | 1.66:1 | **Fail — never use white text on gold** |
| `#FFFFFF` on `#F8D30C` | 1.47:1 | **Fail** |

## 6. Typography

- **Official and verified:** the HTU website loads **Poppins** (Google Fonts,
  weights 100–900) as its global typeface. Montserrat and Raleway appear only in
  the slider plugin.
- **Proposed design interpretation:** Poppins 400 for body, 500 for controls and
  navigation, 600 for headings and the wordmark, 700 reserved for emphasis.
  Load only weights 400–700 with `display=swap`.
- Fallback stack: `system-ui, -apple-system, "Segoe UI", Arial, sans-serif`.
- Poppins is licensed under the SIL Open Font License 1.1.

## 7. Logo placement and sizing

| Placement | Display height | Notes |
| --- | --- | --- |
| Header | 46 px desktop / 40 px mobile | Paired with “Holy Trinity University” and “Enrollment System” |
| Login brand panel | 108 px desktop / 52 px mobile | Standalone with alternative text |
| Footer | 42 px | Decorative beside the university name (`alt=""`) |
| Favicon | Official 32 / 180 / 192 px files | No resampling |

Clear space: at least one-quarter of the seal height on all sides. Minimum
display height 28 px. Always scale proportionally.

## 8. Accessibility

- Maintain a minimum 4.5:1 contrast for body text and 3:1 for large text.
- Never use white text on `#FFBE00` or `#F8D30C`.
- Keep the visible keyboard focus ring (`#FFBE00`, 3 px) and the skip link.
- Retain text labels beside status colours; colour alone is not a signal.
- Respect `prefers-reduced-motion`.
- Tables remain usable on narrow screens through horizontal wrappers.

## 9. Attribution and academic-project note

The official marks belong to Holy Trinity University and are used solely to
identify the institution in a course project. This application is not operated,
endorsed, or sponsored by HTU. See `docs/brand/NOTICE.md` for the full notice and
asset provenance.
