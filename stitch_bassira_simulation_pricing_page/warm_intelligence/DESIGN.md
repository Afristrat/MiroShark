---
name: Warm Intelligence
colors:
  surface: '#fff8f6'
  surface-dim: '#ead6cf'
  surface-bright: '#fff8f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff1ec'
  surface-container: '#ffeae2'
  surface-container-high: '#f9e4dd'
  surface-container-highest: '#f3ded7'
  on-surface: '#241915'
  on-surface-variant: '#57423a'
  inverse-surface: '#3a2e29'
  inverse-on-surface: '#ffede7'
  outline: '#8a7269'
  outline-variant: '#dec0b6'
  surface-tint: '#a13f0f'
  primary: '#a13f0f'
  on-primary: '#ffffff'
  primary-container: '#ff8551'
  on-primary-container: '#6d2400'
  inverse-primary: '#ffb598'
  secondary: '#006d44'
  on-secondary: '#ffffff'
  secondary-container: '#98f2be'
  on-secondary-container: '#067148'
  tertiary: '#006971'
  on-tertiary: '#ffffff'
  tertiary-container: '#00b9c7'
  on-tertiary-container: '#00444a'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbce'
  primary-fixed-dim: '#ffb598'
  on-primary-fixed: '#370e00'
  on-primary-fixed-variant: '#7f2b00'
  secondary-fixed: '#9bf5c1'
  secondary-fixed-dim: '#7fd8a6'
  on-secondary-fixed: '#002111'
  on-secondary-fixed-variant: '#005232'
  tertiary-fixed: '#87f3ff'
  tertiary-fixed-dim: '#48d9e7'
  on-tertiary-fixed: '#002023'
  on-tertiary-fixed-variant: '#004f55'
  background: '#fff8f6'
  on-background: '#241915'
  surface-variant: '#f3ded7'
typography:
  h1:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  h3:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-sm:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.01em
  caption:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 24px
  margin: 32px
---

## Brand & Style

This design system establishes a warm, approachable atmosphere for Bassira, humanizing the complexity of multi-agent simulation. The aesthetic balances professional B2B reliability with a playful, soft personality. By avoiding clinical whites and harsh neons, the interface feels more like a collaborative workshop than a sterile laboratory.

The style is rooted in **Modern Minimalism with Tactile Softness**. It relies on generous white space, organic rounded corners, and a curated "sun-drenched" palette. The goal is to evoke a sense of clarity and optimism, ensuring users feel calm while managing complex data-driven simulations.

## Colors

The palette is anchored by a cream off-white background that reduces eye strain and provides a premium, paper-like quality. The primary orange is energetic but grounded, used for main actions and highlights. Success and warning states use mint and peach respectively—softer, more edible versions of standard semantic colors that maintain the "Playful & Soft" theme.

- **Background**: Use #FAF7F2 for the main canvas.
- **Surface**: Pure white (#FFFFFF) is reserved exclusively for cards and interactive containers to provide lift.
- **Typography**: Use a deep charcoal-brown (#4A4540) instead of pure black to maintain the warm temperature of the UI.

## Typography

This design system pairs **Outfit** for headings with **Manrope** for body text. 

- **Headings**: Outfit provides a geometric, friendly structure. Use tight letter-spacing on larger display sizes to maintain a modern feel.
- **Body**: Manrope ensures high legibility for technical data and agent logs. Its balanced proportions keep the interface professional and readable.
- **Hierarchy**: Use font weight sparingly. Reserve bold weights for primary labels and headers; use the background/neutral contrast to establish hierarchy elsewhere.

## Layout & Spacing

The layout follows a **Fixed Grid** philosophy with expansive margins to create a focused, centered experience. 

- **Grid**: Use a 12-column system with 24px gutters.
- **Rhythm**: Apply a 4px baseline grid. Components should primarily utilize the "md" (24px) spacing value for internal padding to match the card corner radius.
- **Density**: Maintain a low-density feel. Embrace large white space gaps between sections to allow the agent-based data visualizations room to breathe.

## Elevation & Depth

Hierarchy is established through **Ambient Shadows** and tonal layering. Since the background is cream and cards are white, depth is subtle but distinct.

- **Shadows**: Use a single, highly-diffused shadow style for all cards: `0px 12px 32px rgba(74, 69, 64, 0.08)`. The shadow color is tinted with the neutral base (charcoal-brown) to keep it warm.
- **Layering**: Only two levels of elevation are permitted: the background floor and the raised card surface. Avoid stacking cards on cards; use subtle 1px borders (#EBE5DA) for nested divisions within a card.

## Shapes

The shape language is defined by extreme softness. 

- **Cards**: All primary containers must use a **24px (1.5rem)** radius.
- **Interactive Elements**: Buttons and input fields use a **12px (0.75rem)** radius to complement the larger cards.
- **Visual Style**: Avoid all sharp corners. Even progress bars and selection indicators should use fully rounded (pill) caps.

## Components

- **Buttons**: Primary buttons are solid Orange (#FF8551) with white text. Secondary buttons use a cream-tinted stroke. All buttons feature a 12px radius and 16px horizontal padding.
- **Cards**: The signature component of this design system. Always white, 24px radius, with the ambient shadow. Use for agent profiles, simulation controls, and data summaries.
- **Input Fields**: Soft-filled with a slightly darker cream than the background. On focus, use a 2px Orange stroke.
- **Chips/Badges**: Use pill-shaped containers with light-tint backgrounds of the semantic colors (e.g., Mint #7FD8A6 at 15% opacity for "Active" agents).
- **Agent Nodes**: Represent agents in the simulation as rounded circles or "squircle" shapes to maintain the playful aesthetic.
- **Lists**: Use generous vertical padding (16px) and subtle dividers to keep simulation logs legible.