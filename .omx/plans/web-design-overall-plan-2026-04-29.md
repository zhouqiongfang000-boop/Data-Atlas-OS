# Data Atlas Web Design Plan

Date: 2026-04-29
Mode: `$plan` + `ui-ux-pro-max`
Scope: Overall webpage design direction and implementation plan for the Vue/Vite frontend.

## Requirements Summary

The product should present as a professional, shippable data and image analysis workspace named **Data Atlas**, not as a marketing landing page. The core experience is an authenticated command workspace for CSV data analysis, image processing, AI-assisted interpretation, user account management, and admin operations.

Grounding facts:
- The frontend stack is Vue 3, Vite, Vue Router, Naive UI, Arco Design Vue, ECharts, and GSAP in `D:\桌面\毕业设计\frontend\package.json:12`, `D:\桌面\毕业设计\frontend\package.json:15`, `D:\桌面\毕业设计\frontend\package.json:16`, `D:\桌面\毕业设计\frontend\package.json:17`, and `D:\桌面\毕业设计\frontend\package.json:18`.
- The authenticated route surface already includes `/home`, `/workspace/data`, `/workspace/image`, `/account`, and admin-only `/admin` in `D:\桌面\毕业设计\frontend\src\router\index.js:23` through `D:\桌面\毕业设计\frontend\src\router\index.js:27`.
- The current layout already carries the `Data Atlas` identity and top navigation in `D:\桌面\毕业设计\frontend\src\layouts\PlatformLayout.vue:4`, `D:\桌面\毕业设计\frontend\src\layouts\PlatformLayout.vue:8`, and `D:\桌面\毕业设计\frontend\src\layouts\PlatformLayout.vue:13`.
- Existing design guidance says to keep Data Atlas identity consistent, use Naive UI or Arco for structural controls, and verify each UI pass with `npm run build` plus a browser check in `D:\桌面\毕业设计\docs\ui-design-foundation.md:26`, `D:\桌面\毕业设计\docs\ui-design-foundation.md:29`, and `D:\桌面\毕业设计\docs\ui-design-foundation.md:30`.

## Product Positioning

**Design phrase:** precise command workspace with analytical warmth.

Data Atlas should feel like a compact operations cockpit: confident, readable, data-literate, and calm. It can keep the current dark technical atmosphere, but the interface should not become pure neon, pure blue-purple, or decorative sci-fi. The design should make data files, chart actions, image previews, and AI recommendations immediately scannable.

Primary audience:
- Student/project evaluator who needs to see that the system is coherent and complete.
- End user who uploads CSV/image assets, inspects quality, performs analysis, and saves outputs.
- Admin user who needs quiet, dense, reliable management screens.

## Design System

### Visual Tone

Use a **dark graphite command center** as the master shell, balanced with light operational surfaces where data tables, forms, and charts need high legibility.

Recommended visual hierarchy:
- Shell background: dark graphite / midnight, low-noise mesh only.
- Primary accent: Data Atlas blue for navigation, primary buttons, selected states.
- Secondary accents: amber for highlights, teal for system freshness, restrained lime only for homepage signal accents.
- Data surfaces: white or near-white cards for tables, forms, chart canvases, and admin workflows.
- Effects: subtle glass only on global shell and command bars; solid surfaces for repeated cards and tools.

Avoid:
- Letting the homepage lime palette dominate every page.
- Mixing large glass panels, heavy gradients, neon glows, and enterprise tables in the same content layer.
- Hero sections that look like a marketing site after login.
- Cards nested inside larger decorative cards unless the inner card is a repeated data item.

### Token Direction

Current global tokens exist in `D:\桌面\毕业设计\frontend\src\style.css:2` through `D:\桌面\毕业设计\frontend\src\style.css:26`.

Proposed token families:
- `--color-bg-app`: dark graphite shell.
- `--color-surface`: white data surface.
- `--color-surface-muted`: cool light gray panel.
- `--color-text-primary`: near-black on light surfaces, near-white on dark shell.
- `--color-text-muted`: blue-gray with AA contrast.
- `--color-primary`: Data Atlas blue.
- `--color-accent-amber`: important highlights.
- `--color-accent-teal`: success/processing.
- `--color-danger`: destructive and error state.
- `--radius-card`: 8px for repeated cards and tool panels.
- `--radius-shell`: 12px for app shell, drawers, and command bars.
- `--shadow-raised`: one consistent hover/elevation shadow.

### Typography

Use the current font chain from `D:\桌面\毕业设计\frontend\src\style.css:48` as the base: `"Inter", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif`.

Rules:
- Body text starts at 16px with 1.5+ line height.
- Use 12-13px only for labels, badges, overlines, and table metadata.
- Use tabular figures for metrics, table numbers, image dimensions, and chart values.
- Avoid negative letter spacing; reserve uppercase tracking only for small overline labels.

### Components

Use existing dependencies with a clear split:
- Naive UI: workspace drawers, tabs, inputs, notifications, dark app-like controls.
- Arco Design Vue: admin tables, forms, data entry, pagination, and enterprise controls.
- ECharts: charts and analytical visualizations.
- GSAP: restrained page entrance and state transitions only; every motion must respect reduced motion.

The repository already documents this split in `D:\桌面\毕业设计\docs\ui-design-foundation.md:10` through `D:\桌面\毕业设计\docs\ui-design-foundation.md:16`.

## Information Architecture

### `/login` and `/register`

Role: secure brand gateway.

Direction:
- Keep the immersive two-column auth scene, but make form readability the dominant priority.
- Fix/verify Chinese copy encoding before styling pass.
- Keep one primary action per mode.
- Preserve animated data-board elements only if they do not reduce contrast or distract from the form.

### `/home`

Role: operational command home, not landing page.

Current homepage has a left sidebar and dashboard structure in `D:\桌面\毕业设计\frontend\src\views\styles\dashboard-home.css:88`, `D:\桌面\毕业设计\frontend\src\views\styles\dashboard-home.css:317`, and `D:\桌面\毕业设计\frontend\src\views\styles\dashboard-home.css:449`.

Direction:
- First viewport should show current user, workspace readiness, file/image counts, recent activity, and direct actions.
- Keep action tiles for data workspace and image workspace.
- Reduce decorative orbit/glow weight and reserve lime for status accents.
- Replace any placeholder-like hero copy with real task-oriented labels.

### `/workspace/data`

Role: main analytical workspace.

Current structure already separates command header, hero grid, workflow section navigation, sidebar, right panel, and AI dock in `D:\桌面\毕业设计\frontend\src\views\DataWorkspace.vue:8`, `D:\桌面\毕业设计\frontend\src\views\DataWorkspace.vue:36`, `D:\桌面\毕业设计\frontend\src\views\DataWorkspace.vue:79`, `D:\桌面\毕业设计\frontend\src\views\DataWorkspace.vue:83`, and `D:\桌面\毕业设计\frontend\src\views\DataWorkspace.vue:95`.

Direction:
- Promote a three-zone model: asset rail, active workflow canvas, contextual AI dock.
- Keep workflow stages: Overview, Preparation, Exploration, Visualization, Assets/Export.
- Make selected file, selected column, chart type, and AI status permanently visible.
- Use dense but calm panels; the page should feel faster to scan than a long document.

### `/workspace/image`

Role: image processing studio.

Current structure already has header, sidebar/library, canvas grid, and sticky control area in `D:\桌面\毕业设计\frontend\src\views\ImageWorkspace.vue:4`, `D:\桌面\毕业设计\frontend\src\views\ImageWorkspace.vue:23`, `D:\桌面\毕业设计\frontend\src\views\ImageWorkspace.vue:24`, `D:\桌面\毕业设计\frontend\src\views\ImageWorkspace.vue:110`, and `D:\桌面\毕业设计\frontend\src\views\ImageWorkspace.vue:467`.

Direction:
- Mirror the data workspace mental model: left asset library, center before/after canvas, right parameter stack.
- Keep preview, quality metrics, OCR, dominant colors, and history grouped by task.
- Make preview dimensions and save/export state obvious.
- Ensure image panels have stable aspect ratios to prevent layout jumps.

### `/account`

Role: personal operating profile.

Direction:
- Keep account identity, usage metrics, security actions, and activity in a quiet light surface.
- Remove decorative weight; this page is for review and self-service.
- Primary actions: update profile/security, return to workspace.

### `/admin`

Role: enterprise management.

Direction:
- Prefer Arco-style dense tables and forms.
- Reduce hero height; admin users need totals, filters, user table, and account actions above decorative branding.
- Use semantic status badges and clear destructive/role-changing states.

## Implementation Plan

### Phase 1: Copy and Encoding Baseline

1. Read Vue templates with explicit UTF-8 and audit visible Chinese labels, placeholders, aria labels, and button text.
2. Repair only confirmed broken strings; do not rewrite copy just because the terminal displays mojibake under a non-UTF-8 code page.
3. Verify the browser renders Chinese copy correctly on auth, home, data workspace, image workspace, account, and admin pages.

Acceptance:
- No visible mojibake on any route.
- No malformed template attributes caused by broken quotes or copied text.
- All icon-only or compact buttons have readable `aria-label` text.

### Phase 2: Master Design Tokens

1. Consolidate colors, radius, shadows, spacing, and transition tokens in `D:\桌面\毕业设计\frontend\src\style.css`.
2. Reduce repeated page-specific one-off colors where they are equivalent to master tokens.
3. Keep page overrides only where the page has a real role difference, such as homepage signal accents or admin table density.

Acceptance:
- Primary, warning, success, danger, surface, text, radius, and shadow tokens exist once.
- Repeated cards/tool panels use the same radius and elevation scale.
- Light data surfaces and dark command shell both meet contrast targets.

### Phase 3: Navigation and Shell

1. Refine `PlatformLayout.vue` as the authenticated shell for all non-home pages.
2. Keep `/home` as a special full-screen workspace dashboard, but make navigation back to workspaces obvious.
3. Ensure sticky topbar and back-to-top controls do not cover content on mobile.

Acceptance:
- Navigation active states are visible and keyboard reachable.
- Mobile layout has no horizontal scroll at 375px.
- The current role controls admin navigation without visual layout shifts.

### Phase 4: Page-Level Redesign Passes

1. Auth pages: brand gateway plus clear form.
2. Home: command overview with real data signals and direct workflow entry.
3. Data workspace: workflow-first analytical canvas.
4. Image workspace: before/after processing studio.
5. Account: user metrics and self-service.
6. Admin: dense operational management.

Acceptance:
- Each page has one primary job and one dominant action path.
- Loading, empty, success, warning, and error states are present where API data is involved.
- Structural controls come from Naive UI or Arco when appropriate.

### Phase 5: Interaction and Motion

1. Keep motion to page entry, panel expansion, hover/press feedback, and AI drawer transitions.
2. Use transform/opacity only for animation.
3. Add or verify `prefers-reduced-motion` behavior.

Acceptance:
- No animation blocks user input.
- Motion duration stays around 150-300ms for micro-interactions.
- Reduced motion mode disables or simplifies nonessential animation.

### Phase 6: Responsive and Accessibility QA

1. Test 375px, 768px, 1024px, and 1440px widths.
2. Verify keyboard navigation through topbar, workspace pills, file list, chart controls, AI dock, admin table actions, and forms.
3. Check color contrast for dark and light surfaces.
4. Confirm chart and image preview regions have accessible summaries/labels.

Acceptance:
- No horizontal scrolling except intentional data tables with a visible table shell.
- Touch targets are at least 44x44px.
- Focus states are visible.
- Normal text contrast is at least 4.5:1.

## Risks and Mitigations

- Risk: Existing page styles drift between neon homepage, glass command deck, light admin, and image studio.
  Mitigation: Establish master tokens first, then allow controlled page-level overrides.
- Risk: Naive UI and Arco Design Vue can create inconsistent component language.
  Mitigation: Keep Naive UI for workspace panels and Arco for admin/data-entry surfaces.
- Risk: Decorative backgrounds compete with dense data.
  Mitigation: Use decorative elements only in shell/header layers, not behind tables/forms/charts.
- Risk: PowerShell default output can display UTF-8 Chinese as mojibake, creating false positives during review.
  Mitigation: Read files with explicit UTF-8 and verify in the browser before repairing copy.
- Risk: The local `ui-ux-pro-max` search script is unavailable because the installed `scripts` and `data` entries point to missing directories.
  Mitigation: Follow the skill's documented rule categories manually until the local skill package is repaired.

## Verification Steps

Run after each implementation slice:

```powershell
cd D:\桌面\毕业设计\frontend
npm run build
```

Browser QA:
- Open `/login`, `/register`, `/home`, `/workspace/data`, `/workspace/image`, `/account`, and `/admin`.
- Check 375px, 768px, 1024px, and desktop widths.
- Confirm no visible mojibake in the browser, overlap, or clipped buttons.
- Confirm keyboard focus and reduced-motion behavior.

Static checks:
- Search for raw page-specific hex sprawl after token consolidation.
- Search for icon-only buttons without `aria-label`.
- Search for repeated card radius/shadow values that should be tokenized.

## Follow-Up Staffing Guidance

Solo route:
- One executor can implement Phase 1 and Phase 2.
- A verifier should inspect responsive/accessibility evidence after every 1-2 pages.

Parallel route:
- Executor A: global tokens, shell, auth/home.
- Executor B: data workspace and AI dock.
- Executor C: image workspace.
- Executor D: account/admin.
- Verifier: build, browser screenshots, responsive/a11y checklist.

Recommended execution order:
1. Repair text/copy.
2. Consolidate tokens.
3. Redesign shell and auth.
4. Redesign home.
5. Redesign workspaces.
6. Redesign account/admin.
7. Run final build and browser QA.

## Known Gaps

- No source code was changed by this plan.
- The `ui-ux-pro-max` CLI search step could not run because its local script path is not present.
- Visual QA still needs actual browser screenshots after implementation.
