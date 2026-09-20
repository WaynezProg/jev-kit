# Browser decision-loop fixture

This is a small, authored **synthetic** local HTML app for matched browser-loop benchmark runs. It is not evidence about a live website or general web performance. The app itself knows the desired path and gives immediate wrong-route feedback, so it is a synthetic semantic wizard, not a realistic arbitrary-site recovery task.

Serve this directory from its parent with Python's standard library, then open `fixture/index.html?task=t9f3k2`. The query selects one fixed task; a missing or unknown ID opens the first pilot task.

Each task has four sequential screens. A screen exposes the natural-language goal, one stage prompt, and three visible choices. The next screen is not rendered until the correct choice is selected. Each visible choice is a button with `data-option` set to an opaque ID. The document body exposes:

- `data-state="active"` while a stage can be chosen;
- `data-state="error"` after an incorrect choice; and
- `data-state="done"` once all stages are complete.

The body also has `data-task` with the opaque task ID. The stable visible selectors are `[data-goal]`, `[data-prompt]`, `[data-option]`, and `#selection` (after completion). A wrong choice is recoverable: it replaces the choices with a clear outcome and a **Back** button. Back restores the same stage without advancing it. Reloading the page resets the task.

The fixture intentionally does not put an answer, correctness indicator, or rationale in the visible page or `data-option` attributes. `tasks.json` stores the authored gold path and stage rationale separately for the benchmark runner. After a successful run, a checker may inspect `window.fixtureState.taskId`, `.stage`, and `.selected` (opaque option IDs); browser-model inputs must use only the visible page and buttons.

There are two pilot tasks and eight held-out tasks. The held-out set contains four product-selection and four developer-documentation navigation workflows.
