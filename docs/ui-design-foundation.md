# UI Design Foundation

This project is prepared for iterative UI redesign with three layers:

1. `ui-ux-pro-max`
   - Installed as a local Codex skill.
   - Use it as the design direction layer for tokens, layout choices, accessibility checks, dashboard patterns, and visual QA.
   - Restart Codex before expecting the new skill to appear in the active skill list.

2. `naive-ui` and `@arco-design/web-vue`
   - Installed in the frontend package.
   - Listed from `frontend/src/plugins/ui-libraries.js`.
   - Import components per page or feature area instead of globally registering both libraries.
   - Prefer one library per page or feature area when possible:
     - Naive UI for modern dark workspace components and app-like panels.
     - Arco Design Vue for admin tables, forms, data entry, and enterprise controls.

3. Galaxy / Uiverse
   - Use as a curated inspiration source, not a global dependency.
   - Source: https://github.com/uiverse-io/galaxy
   - Pull individual CSS or Tailwind elements only when they match the Data Atlas style.
   - Convert selected elements into local Vue components before use.

Guardrails for later UI work:

- Keep the Data Atlas identity consistent across pages.
- Do not mix multiple decorative styles on the same screen.
- Use Galaxy for small accents such as loaders, feature cards, buttons, and empty states.
- Use Naive UI or Arco for structural controls such as forms, tables, modals, menus, tabs, and notifications.
- Verify each UI pass with `npm run build` and a browser check.
