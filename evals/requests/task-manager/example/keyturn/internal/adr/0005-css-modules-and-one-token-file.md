# 0005. CSS Modules and one token file for the look of the pages

- Status: accepted
- Date: 2026-11-08
- Serves: R-10
- Needs client agreement: no

## Context

R-10 asks for tidy pages on a computer and on a phone (AC-10 to AC-13). The requirements' "Look" says `Look baseline: standard` and `UI library: none`, and the client left the look to keyturn on decision card 3, so the architect takes the best practice at this time for a React application built with Vite, the stack of [ADR 0004](0004-react-and-vite-for-the-web-client.md). The `react-spa` profile names CSS Modules with CSS custom properties as its default method, and fixes how the pages use the tokens, not the method ([ADR 0067 in keyturn](../../../../../../../docs/adr/0067-design-decides-how-the-look-is-built.md), [ADR 0072 in keyturn](../../../../../../../docs/adr/0072-profiles-fix-styling-principles-not-the-tool.md)).

Checked on 2026-11-08 in the current documentation of Vite (its CSS features: CSS Modules for `*.module.css` files, and CSS custom properties passed through as they are) and of React (styling is left to CSS; no styling method is built in).

## Options considered

1. **CSS Modules, with the tokens as CSS custom properties in one file**: each component's styles next to it, with class names Vite scopes to the component, so one page's styles cannot change another's; nothing to add to the project, since Vite builds them; the tokens in one place.
2. **One global stylesheet, with the same tokens**: nothing to add either, but every class name is shared by every page, so a rule for one page can change another, and the file grows with every page.
3. **Tailwind CSS**: widely used, with its own spacing and type scales, but a new runtime dependency the client would agree to, with a build plugin, for three pages; its own scale has to be replaced by the tokens, and the utilities with widths built in (for example `border`) stay, which only the review finds.
4. **A CSS-in-JS library** (styles written in TypeScript): a new runtime dependency, and code that runs in the browser to apply the styles, for no gain on three pages.

## Maintainability after delivery

- Weight: the same as fit: the requirements do not say who maintains the deliverable.
- Less known choice: no. Tailwind CSS is very widely used too, but CSS Modules and CSS custom properties are part of what Vite and the browser already do, so whoever maintains the pages needs to know only CSS.

| Option | Use | Modern | Documentation | People | Stability |
|---|---|---|---|---|---|
| CSS Modules and custom properties | a feature of the stack: Vite builds `*.module.css` files, and custom properties are CSS (known as the stack, ADR 0004) | "Any CSS file ending with `.module.css` is considered a CSS modules file", and Vite recommends native CSS variables (vite.dev/guide/features, checked 2026-11-28) | that guide (checked 2026-11-28) | anyone who knows CSS and Vite | part of Vite, pinned with it; no package of its own |
| One global stylesheet | not compared: it does not fit (a rule for one page can change another) | | | | |
| Tailwind CSS | 98,866 stars, 175 million npm downloads in the week to 2026-11-27, latest release 2026-11-06 (github.com, api.npmjs.org, checked 2026-11-28) | its own guide installs it as a Vite plugin (tailwindcss.com/docs/installation/using-vite, checked 2026-11-28) | its own documentation (checked 2026-11-28) | many people know it (its stars and downloads) | its last major release moved the configuration from a JavaScript file to CSS and renamed utilities (tailwindcss.com/docs/upgrade-guide, checked 2026-11-28) |
| A CSS-in-JS library | not compared: it does not fit (code that runs in the browser to apply the styles, for three pages) | | | | |

## Decision

CSS Modules, with the tokens as CSS custom properties in `web/src/styles/tokens.css`, as the design's "Look" lists them (option 1).

## Reasons

- It is what Vite's documentation offers for scoped styles, with no dependency, so the client has nothing to agree to and nothing new to keep up to date.
- One token file gives every page the same spacing, sizes, and colors, which is what AC-10 and AC-11 check; the scoped class names keep the pages from changing each other.
- Options 3 and 4 add a dependency the tidy minimum does not need.

## Consequences

- The developer writes `web/src/styles/tokens.css` with exactly the design's tokens, imports it once in the entry point, and styles each component in a `*.module.css` file with `var(--<token>)`; the reviewer checks both against the design.
- A later "worked out" look, or an approved look, changes the tokens in the same file, through the design.
