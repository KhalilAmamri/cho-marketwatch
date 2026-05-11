# Figures Folder Guide

This folder contains the final visual assets that will replace placeholder boxes used in the LaTeX chapters.

## Recommended naming

- fig_01_architecture_globale.png
- fig_02_processus_asis.png
- fig_03_processus_tobe.png
- fig_04_modele_erd.png
- fig_05_dashboard_overview.png
- fig_06_retail_presence.png
- fig_07_operational_visibility.png

## Insertion workflow

1. Export screenshots/diagrams in PNG or PDF (high resolution).
2. Place files in this folder with stable names.
3. Replace each `\figureplaceholder{...}{...}` with a real `\includegraphics` block.
4. Recompile and verify numbering/captions.

## Quality checklist

- Minimum width 1600px for UI screenshots.
- Keep text readable after PDF export.
- Use consistent crop and margin style.
- Avoid exposing sensitive data in screenshots.
