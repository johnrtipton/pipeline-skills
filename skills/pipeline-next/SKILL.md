---
name: pipeline-next
description: >
  Pick the next task (or group of related tasks) from ROADMAP.md and set up
  a pipeline state file. Reads the roadmap, filters by milestone/priority,
  groups related small features into batches, checks what's already done,
  and creates .pipeline-state/<branch>.json from the template.
  Run /pipeline-run after this to execute the stages.
---

# Pipeline Next — Pick a Task and Initialize

Pick the next task from the project's ROADMAP.md and create a pipeline state file.

**Usage**:
- `/pipeline-next` — next highest-priority task from first milestone
- `/pipeline-next --milestone v0.4.0` — next task from v0.4.0
- `/pipeline-next --milestone v0.4.0 --priority P1` — next P1 task
- `/pipeline-next --feature "dj-value"` — specific feature by keyword
- `/pipeline-next --list` — list available tasks without starting
- `/pipeline-next --milestone v0.4.0 --group` — auto-group remaining tasks and pick next group
- `/pipeline-next --milestone v0.4.0 --list --group` — show proposed groups without starting

## Steps

### 1. Find and read ROADMAP.md

Look for: `ROADMAP.md`, `docs/ROADMAP.md`, `docs/roadmap.md`

### 2. Parse the Priority Matrix

The table at the top maps features to priorities (P0-P3). Parse it. Items with ~~strikethrough~~ or ✅ are completed — skip them.

### 3. Parse milestones and features

Scan for `### Milestone: vX.Y.Z — Title` sections. Within each, find `**Feature Name**` entries. Skip sections: Completed, Future, Contributing, Investigate, Differentiators, Parity Tracker.

For each feature extract: name, milestone, section, priority (from matrix), issue number (#NNN if present), type (bugfix if section has "Bug Fix" or description mentions fixing/broken, else feature), and the full spec text.

### 4. Filter and select

Apply the user's filters (milestone, priority, feature keyword). Sort by priority (P0 first), then bug fixes before features.

### 5. Check what's already done

For each matching task, check:
- `.pipeline-state/<branch>.json` exists with `completed_at` set → done
- `gh pr list --state merged --head <branch>` finds a merged PR → done
- `.pipeline-state/<branch>.json` exists without `completed_at` → **resume this one**

Print status of all matching tasks.

### 6. Group related tasks (--group mode)

If `--group` is specified, analyze the remaining (not-done) tasks and group them by relatedness. Tasks should be grouped when they:

- **Touch the same files** — e.g., multiple `dj-*` attributes all modify `03-event-binding.js`
- **Share a pattern** — e.g., all "add HTML attribute" features follow the same implementation pattern
- **Are small and related** — e.g., multiple CSS class toggles, multiple client-side-only features
- **Belong to the same ROADMAP section** — e.g., all under "Quick Wins"

**Grouping rules:**
- Each group should have a clear theme name (e.g., "Event attributes", "UI feedback attributes")
- Max ~5-6 tasks per group (keeps the implementation manageable)
- Large/complex tasks (like "Transition/priority updates") stay solo
- Bug fixes are never grouped with features

**Suggested groupings — these are examples, not exhaustive. Analyze the actual ROADMAP tasks to propose project-specific groups.**

djust core (v0.4.0 quick wins):

| Group | Tasks | Theme |
|---|---|---|
| Event attributes | `_target` param, `dj-disable-with`, `dj-lock`, `dj-mounted` | Event handling in client JS |
| Scoping attributes | Window/document scoping, `dj-click-away`, `dj-shortcut` | Window/document event binding |
| UI feedback | `dj-cloak`, `dj-page-loading`, Connection state CSS, `dj-scroll-into-view` | CSS class state management |
| Utility attributes | `dj-copy`, `dj-auto-recover`, `dj-debounce`/`dj-throttle` HTML | Small standalone client features |
| Document metadata | `live_title` & document metadata | Server + client metadata |
| Reconnection | Form recovery, Reconnection backoff with jitter | WebSocket reconnection path |
| Dev tooling | Error messages, `djust_doctor`, Latency simulator | Developer experience |

djust-components (v1.4):

| Group | Tasks | Theme |
|---|---|---|
| CSS Batch 1 | Kbd (#38), Copy Button (#37), Rating (#36), Code Block (#34), Collapsible (#39) | Simple inline component CSS |
| CSS Batch 2 | Popover (#32), Sheet/Drawer (#41), Context Menu (#42), Command Palette (#45) | Overlay/positioning CSS |
| CSS Batch 3 | Combobox (#31), Color Picker (#40), Date Picker (#46), File Dropzone (#47) | Form control CSS |
| CSS Batch 4 | Notification Center, Tree View, Gauge, Carousel, Virtual List, Kanban, ToC, Split Pane, Rich Text Editor | Complex component CSS |
| Trivial layout components | Aspect Ratio (#116), Sticky Header (#171), Page Header (#179), Description List (#134), Callout (#67) | Simple CSS-only layout, zero JS |
| Small feedback components | Status Indicator (#128), Notification Badge (#105), Loading Overlay (#104), Announcement Bar (#106) | Simple feedback/status indicators |
| Simple form primitives | Label (#66), Fieldset (#147), Toggle Group (#61), Input Group (#64) | Form layout building blocks |
| Client-side utilities | Scroll to Top (#125), Relative Time (#146), Theme Toggle (#138), Scroll Area (#62) | Small JS + CSS, no server events |
| Code & copy components | Code Snippet (#139), Copyable Text (#153), Copy Button CSS | Code display + clipboard |
| Real-time djust-native | Streaming Text (#129), Connection Status Bar (#175), Live Counter (#176), Server Event Toast (#177) | WebSocket-powered components |
| New form inputs | Multi-select (#53), OTP Input (#58), Number Stepper (#59), Tag Input (#63) | Form input components |
| Rich display components | Rich Select (#103), Split Button (#133), Progress Circle (#124), Segmented Progress (#107) | Enhanced display components |
| Component classes | Alert, StatCard, Tag/Chip, Toast, Progress, Spinner, Switch class expansion | Python class APIs |
| Data Table Pro P1 | Sorting, selection, filtering, search, ARIA, DataTableMixin | SOLO — too large to group |
| Data Table Pro P2 | Inline editing, resize, reorder, frozen cols, density, responsive | SOLO — too large to group |
| Data Table Pro P3 | Row expansion, bulk actions, export, virtual scroll, faceted filter | SOLO — too large to group |

djust-components (v1.5):

| Group | Tasks | Theme |
|---|---|---|
| Form essentials | Slider (#82), Search Input (#83), Password Input (#84), Autocomplete (#85) | Missing form inputs |
| Confirmation patterns | Confirmation Dialog (#75), Popconfirm (#180) | User confirmation UX |
| Cascading forms | Dependent Select (#108), Currency Input (#109), Form Validation Display (#110) | Form interaction patterns |
| App chrome | Sidebar Nav (#86), Navigation Menu (#90), App Shell (#167) | Application layout shell |
| Toolbar & editing | Toolbar (#87), Inline Edit (#88), Filter Bar (#166) | Action bar patterns |
| Social components | Avatar Group (#89), Hover Card (#91), Notification Popover (#168) | User-facing social UX |
| AI chat UI | Conversation Thread (#130), AI Thinking Indicator (#160), Multimodal Input (#159), Feedback Widget (#149) | AI application interface |
| AI trust UI | Approval Gate (#155), Source Citation (#156), Model Selector (#131), Token Counter (#132) | AI safety and transparency |
| Collaboration | Chat Bubble (#55), Presence Avatars (#56), Mentions Input (#57) | Real-time collaboration |
| Text display | Expandable Text (#118), Truncated List (#150), Inline Markdown Preview (#169) | Text truncation/preview |
| Loading patterns | Skeleton Factory (#144), Content Loader / Suspense (#152) | Loading state management |
| Data export/import | Export Dialog (#161), Import Wizard (#162), Audit Log Table (#163) | Enterprise data workflows |
| Django integration | Django Form Renderer (#73), ModelForm Table (#74) | Django ecosystem bridges |
| Data Table Pro P4 | Column formatters, footer aggregation, conditional styling, multi-level headers | SOLO — too large to group |
| Data Table Pro P5 | CSV import, computed columns, cell merge, column expressions | SOLO — too large to group |

Print the proposed groups with `--list --group`. Without `--list`, pick the highest-priority group.

### 7. Create the state file

Read the template file DIRECTLY:

```bash
# For features:
cat ~/online_projects/ai/pipeline-skill/templates/feature-state.json
# For bugfixes:
cat ~/online_projects/ai/pipeline-skill/templates/bugfix-state.json
# For refactors:
cat ~/online_projects/ai/pipeline-skill/templates/refactor-state.json
```

**For a single task:** Copy template, fill in task_description, branch_name, etc.

**For a group (--group mode):** Copy the feature template, then:
- `task_description`: Include ALL tasks in the group with their specs:
  ```
  ## Batch: <group theme>

  Implement these related features as a single PR:

  ### 1. <task name>
  <spec from ROADMAP>

  ### 2. <task name>
  <spec from ROADMAP>
  ...
  ```
- `branch_name`: `feat/<group-slug>` (e.g., `feat/event-attributes`, `feat/ui-feedback-attrs`)
- The Planning stage will plan all tasks together
- The Implementation stage will implement all tasks in sequence
- One PR covers the entire group
- Add a `"batch_tasks"` field to the state file listing the individual task names:
  ```json
  "batch_tasks": ["_target param", "dj-disable-with", "dj-lock", "dj-mounted"]
  ```

Write to `.pipeline-state/<branch-name>.json`. Ensure `.pipeline-state/` is in `.gitignore`.

### 8. Output

**Single task:**
```
═══════════════════════════════════════════
  Task selected: <name>
  Type: <feature|bugfix> | Priority: <P0-P3>
  Branch: <branch-name>
  State: .pipeline-state/<file>.json
  Stages: <N> (from template)
═══════════════════════════════════════════
```

**Batch group:**
```
═══════════════════════════════════════════
  Group selected: <group theme>
  Tasks: <count> features
  Branch: feat/<group-slug>
  State: .pipeline-state/<file>.json
  Stages: <N> (from template)

  Included tasks:
  1. <task name>
  2. <task name>
  ...
═══════════════════════════════════════════
```
