---
name: Apex Velocity
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#bbcabf'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#86948a'
  outline-variant: '#3c4a42'
  surface-tint: '#4edea3'
  primary: '#4edea3'
  on-primary: '#003824'
  primary-container: '#10b981'
  on-primary-container: '#00422b'
  inverse-primary: '#006c49'
  secondary: '#adc6ff'
  on-secondary: '#002e6a'
  secondary-container: '#0566d9'
  on-secondary-container: '#e6ecff'
  tertiary: '#ffb95f'
  on-tertiary: '#472a00'
  tertiary-container: '#e29100'
  on-tertiary-container: '#523200'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6ffbbe'
  primary-fixed-dim: '#4edea3'
  on-primary-fixed: '#002113'
  on-primary-fixed-variant: '#005236'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '600'
    lineHeight: '1.2'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style

This design system is engineered for high-performance sports betting, targeting professional traders and serious enthusiasts. The brand personality is clinical, fast, and authoritative, evoking the atmosphere of a high-end trading floor or a futuristic sports arena. 

The aesthetic leverages **Glassmorphism** and **High-Contrast** elements within a dark, immersive environment. It prioritizes data density without sacrificing clarity, using translucent layers to create a sense of depth and focus. The emotional response should be one of "controlled intensity"—a premium, high-fidelity experience that feels both cutting-edge and deeply reliable.

## Colors

The palette is anchored in a deep Obsidian base to reduce eye strain during long sessions.
- **Emerald Green (Primary):** Used exclusively for success states, winning odds, and "Live" indicators. It represents growth and positive action.
- **Azure Blue (Secondary):** Dedicated to market odds, active selections, and primary navigation. It provides a cool, intellectual contrast to the dark base.
- **Amber (Tertiary):** Reserved for "value" alerts, promotional boosts, or cautionary information.
- **Surface Strategy:** Backgrounds use a true black/near-black, while interface cards utilize semi-transparent slates with a subtle background blur (12px - 20px) to achieve the glass effect.

## Typography

The typography system balances the Swiss-style efficiency of **Inter** with the technical precision of **JetBrains Mono**. 
- **Headlines:** Use tight tracking and heavy weights to create a sense of urgency.
- **Data Points:** All numerical values, odds, and timestamps should utilize JetBrains Mono to ensure tabular alignment and a "Pro" instrument feel.
- **Scaling:** On mobile devices, `display-lg` scales down to 32px (`headline-lg`) to maintain readability. 
- **Hierarchy:** Use uppercase labels in JetBrains Mono for metadata (e.g., "MATCH TIME", "WAGER LIMIT") to differentiate from actionable content.

## Layout & Spacing

This design system employs a **Fluid Grid** model with a 12-column structure for desktop. 
- **Density:** To achieve high data density, the base unit is a strict 4px grid. 
- **Margins:** Desktop views utilize a 32px outer margin, while mobile drops to 16px. 
- **Reflow:** On mobile, the 12-column layout collapses to a single-column stack. Odds tables should transition to horizontally scrollable cards or condensed lists.
- **Component Spacing:** Use `md` (16px) for internal card padding and `sm` (8px) for related data groupings within cards.

## Elevation & Depth

Depth is established through **Tonal Glassmorphism** rather than traditional shadows.
- **Level 0 (Base):** Deep Slate #020617.
- **Level 1 (Cards):** Surface color with 60% opacity and a 1px inner stroke of white at 10% opacity to simulate a glass edge.
- **Level 2 (Modals/Popovers):** Higher opacity (80%) with a vibrant backdrop blur (40px) and a subtle outer glow using the Primary or Secondary color (5-10% opacity).
- **Interaction:** On hover, glass cards should increase their inner stroke opacity and background blur intensity to indicate focus.

## Shapes

The design system uses a **Soft (0.25rem)** roundedness approach to maintain a professional, sharp look while appearing modern.
- **Standard UI elements:** 4px (0.25rem) radius.
- **Large Cards/Containers:** 8px (0.5rem) radius.
- **Selection Indicators:** Use "sharp" vertical pills (bar-like) to indicate active tabs or navigation items rather than large rounded buttons.

## Components

- **Buttons:** Primary buttons use a solid Azure Blue with high-contrast white text. Secondary buttons are "Ghost" style with the 1px glass stroke and text color matched to the accent.
- **Odds Chips:** Compact rectangles with a subtle gradient (darker at bottom) and JetBrains Mono text. On "Odds Change," the chip should flash Emerald (up) or Red (down) briefly.
- **Data Lists:** Use alternating row opacities (zebras) for long lists of matches. No borders between rows; use a 1px transparent gap to maintain the grid.
- **Input Fields:** Darker than the surface color, with the Azure Blue used for the focus ring. No labels; use floating placeholders to save vertical space.
- **Status Indicators:** Use small, pulsing neon dots for "Live" events.
- **Bet Slip:** A persistent sidebar (desktop) or bottom sheet (mobile) using a Level 2 elevation to appear "above" the market data.