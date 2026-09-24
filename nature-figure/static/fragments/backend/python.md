# Backend: Python (matplotlib / seaborn)

**Python-only execution rule.** When the user has selected Python, do all figure drawing, previewing, exporting, and visual QA in Python. Do not call R/ggplot2, ComplexHeatmap, patchwork, or any R graphics device to create a temporary preview, fallback export, or layout approximation. If Python or required Python plotting packages are missing, stop before rendering and report the missing dependency. You may still write the Python script, provide `pip`/environment install commands, or ask permission to install dependencies, but do not cross-render the figure in R.

## Python quick-start

```python
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

def apply_figure_typography(multi_panel=False, font_size=None):
    """Set SimSun/Times New Roman and panel-aware point sizes."""
    size = float(font_size if font_size is not None else (12 if multi_panel else 18))
    mpl.rcParams.update({
        "font.family": ["Times New Roman", "SimSun"],
        "font.serif": ["Times New Roman", "SimSun"],
        "font.size": size,
        "axes.labelsize": size,
        "axes.titlesize": size,
        "xtick.labelsize": size,
        "ytick.labelsize": size,
        "legend.fontsize": size,
        "mathtext.fontset": "custom",
        "mathtext.rm": "Times New Roman",
        "mathtext.it": "Times New Roman:italic",
        "mathtext.bf": "Times New Roman:bold",
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.unicode_minus": False,
    })
    return size


def font_properties_for(language="en", size=None, weight="normal"):
    """Return explicit SimSun or Times New Roman properties for text labels."""
    family = "SimSun" if language.lower().startswith("zh") else "Times New Roman"
    return FontProperties(family=family, size=size, weight=weight)


apply_figure_typography(multi_panel=False)
mpl.rcParams.update({
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.8,
    "legend.frameon": False,
})

def save_pub_py(fig, filename, dpi=600):
    fig.savefig(f"{filename}.svg", bbox_inches="tight")
    fig.savefig(f"{filename}.pdf", bbox_inches="tight")
    fig.savefig(f"{filename}.tiff", dpi=dpi, bbox_inches="tight")
```

Use `text.usetex = True` only when LaTeX is installed and math-rich labels are required.

## Going deeper

- `references/api.md` — Python PALETTE, helper function signatures, validation rules.
- `references/template-catalog.md` — validated CSV-driven volcano, ROC, dot-plot, marginal, and paired templates backed by `scripts/plot_templates.py`.
- `references/common-patterns.md` — hero panels, legend-only axes, dark image plates, asymmetric layouts.
- `references/chart-types.md` — radar, 3D sphere, fill_between, scatter patterns.
- `references/tutorials.md` — end-to-end walkthroughs for bars, trends, heatmaps.
- `references/demos.md` — bundled figures4papers Python scripts and output previews.
- `scripts/validate_figure.py` — dependency-free source preflight before rendering and visual QA.
