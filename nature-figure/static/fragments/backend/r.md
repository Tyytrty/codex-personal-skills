# Backend: R (ggplot2 / patchwork / ComplexHeatmap)

**R-only execution rule.** When the user has selected R, do all figure drawing, previewing, exporting, and visual QA in R. Do not call matplotlib/seaborn or any Python graphics device to create a temporary preview, fallback export, or layout approximation. If `Rscript`/R or required R packages are missing, stop before rendering and report the exact blocker. You may still write the R script, provide install commands (for example `install.packages(...)`), or ask permission to install dependencies, but do not cross-render the figure in Python.

## R quick-start

```r
library(ggplot2)
library(patchwork)

figure_base_size <- function(multi_panel = FALSE, font_size = NULL) {
  if (!is.null(font_size)) return(font_size)
  if (multi_panel) 12 else 18
}

figure_font_family <- function(language = "en") {
  if (startsWith(tolower(language), "zh")) "SimSun" else "Times New Roman"
}

theme_figure <- function(multi_panel = FALSE, font_size = NULL) {
  size <- figure_base_size(multi_panel, font_size)
  theme_classic(base_size = size, base_family = figure_font_family("en")) +
    theme(
      axis.line = element_line(linewidth = 0.35, colour = "black"),
      axis.ticks = element_line(linewidth = 0.35, colour = "black"),
      legend.title = element_text(size = size, family = figure_font_family("en")),
      legend.text = element_text(size = size, family = figure_font_family("en")),
      strip.text = element_text(size = size, face = "bold", family = figure_font_family("en")),
      plot.title = element_text(size = size, face = "bold", family = figure_font_family("en")),
      panel.grid = element_blank()
    )
}

theme_set(theme_figure(multi_panel = FALSE))

# Use family = figure_font_family("zh") for Chinese-only labels.

save_pub_r <- function(plot, filename, width_mm = 183, height_mm = 120, dpi = 600) {
  w <- width_mm / 25.4
  h <- height_mm / 25.4
  svglite::svglite(paste0(filename, ".svg"), width = w, height = h)
  print(plot)
  dev.off()
  grDevices::cairo_pdf(paste0(filename, ".pdf"), width = w, height = h, family = "Times New Roman")
  print(plot)
  dev.off()
  ragg::agg_tiff(paste0(filename, ".tiff"), width = w, height = h, units = "in", res = dpi)
  print(plot)
  dev.off()
}
```

## Going deeper

- `references/r-workflow.md` — the R plotting workflow when the user provides R scripts, templates, or data.
- `references/r-template-index.md` — adapt a user-provided or private R template collection without exposing source paths.
- `references/design-theory.md` — typography, color theory, layout rationale, export policy (backend-agnostic).
- `references/nature-2026-observations.md` — real Nature page archetypes to match before choosing layout.
- `scripts/validate_figure.py` — dependency-free static R source preflight before running R and inspecting the rendered outputs.
