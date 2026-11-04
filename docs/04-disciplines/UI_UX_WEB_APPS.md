# UI/UX, Product Design, Websites, and Applications

## Scope

Research, persona/task understanding, information architecture, user flows, wireframes, interaction, visual design, design systems, typography, components, responsive layouts, accessibility, prototypes, front-end, back-end, APIs, state, auth, data persistence, testing, deployment and support.

## Candidate tools

Penpot, Figma, design-token standards, Storybook, browser automation/testing, standard web frameworks and component libraries; native app frameworks where needed. Figma and other hosted products are optional; verify API scopes and terms. Use mature frameworks rather than inventing rendering primitives for production interfaces.

## Product-design process

Brief and user goals → competitive/product research → information architecture → task flow → low-fidelity structure → visual system → high-fidelity screen states → interactive prototype → usability/accessibility review → implementation → automated browser/device tests → analytics/privacy review → release.

## UI quality contract

- Clear hierarchy, spacing system, alignment, responsive behavior, typography scale, contrast, color semantics, icon consistency, state feedback, transitions and empty/loading/error states.
- Keyboard navigation, focus management, semantics, screen-reader labels, reduced motion, text scaling and color-independent meaning.
- Functional flows have real state and data; static mockups cannot be presented as working apps.
- Test at target viewport sizes, browsers, OS and input modes.
- Visual regression baselines are reviewed; dynamic content and anti-alias differences are handled intentionally.
- Production UI must not use SVG/canvas primitives as a shortcut where real component/application design is required; SVG can be an appropriate native icon/vector deliverable when it is the correct medium.

## Software engineering gate

Type checking, lint, unit/integration/e2e tests, accessibility audit, security checks, build, runtime smoke, network behavior, error handling, state persistence, performance and clean deployment must be evidenced.
