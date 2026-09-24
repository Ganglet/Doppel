# Doppel web dashboard

A React dashboard for the Doppel benchmark results. It sits beside the Streamlit app in `dashboard/`, which is unchanged.

The page answers one question: which synthetic-data generator is realistic, useful and private? It has six sections: Overview, Compare, Trade-offs, Privacy, Data and Project. Every chart has a "Show table" view, works with the keyboard, and follows the system light or dark theme (there is also a toggle).

## Run it

You need Node 20 or newer.

```bash
cd web
npm install
npm run dev        # http://localhost:5173
```

To build a static site:

```bash
npm run build      # writes web/dist
npm run preview    # serves it on http://localhost:4173
```

Add `?theme=light` or `?theme=dark` to the address to force a theme.

## Where the numbers come from

The page reads one file, `public/data/dashboard.json`. It holds only aggregates (means, spreads, p-values, the Pareto frontier), never patient rows. Regenerate it from the evaluation results with:

```bash
npm run export-data      # runs scripts/export_data.py from the repo root's results/
```

The script reuses `evaluation.pareto`, so the frontier matches the command-line output exactly. Rerun it whenever new generators or seeds land in `results/`.

The Data section shows the generated tables themselves (a preview, column types and the manifest, as in the Streamlit dashboard) for all 100 evaluated datasets. `npm run export-data` also writes those, from `output/synthetic/eval/` to `public/data/datasets/`. That folder is git-ignored, like `output/synthetic/`, because a generator that memorizes (TVAE) can reproduce real rows. Without it the Data section shows a note on how to generate the files.

## Layout

| Path | What it holds |
|---|---|
| `src/sections/` | The five page sections |
| `src/charts/` | Dot plot, scatter plot and heatmap, drawn as plain SVG |
| `src/components/` | Chart card with table view, legend, tooltip, controls |
| `src/lib/content.js` | Static text: pipeline steps, status matrix, glossary, limits |
| `src/styles.css` | Design tokens for light and dark, and all component styles |

Before merging to `main`, change `docs_ref` in `scripts/export_data.py` from the branch name to `main` so the "Read more" links resolve.
