#!/bin/bash
# Git commit script for CTUFT v1.0 release

cd /root/.openclaw/workspace/uft-clifford-torsion

echo "=== Adding core PDF files ==="
git add paper/main.pdf
git add paper/ctuft_arxiv.pdf
git add paper/supernova_paper.pdf
git add paper/supernova_paper_zh.pdf
git add paper/spectral_collapse.pdf
git add paper/neutrino_time_structure.pdf
git add paper/frb_period_relation.pdf

echo "=== Adding LaTeX sources ==="
git add paper/main.tex
git add paper/ctuft_arxiv.tex
git add paper/supernova_paper.tex
git add paper/supernova_paper_zh.tex
git add paper/github_release_info.txt
git add paper/zenodo_submission_info.txt
git add paper/vixra_submission_info.txt
git add paper/arxiv_submission_info.txt

echo "=== Adding support files ==="
git add paper/spectral_collapse.png

echo "=== Commit ==="
git commit -m "Add CTUFT v1.0 papers and submission materials

Main papers:
- main.pdf (190 pages, full theory)
- ctuft_arxiv.pdf (3 pages, compact version)
- supernova_paper.pdf (5 pages, English)
- supernova_paper_zh.pdf (4 pages, Chinese)

Figures:
- spectral_collapse.pdf/png
- neutrino_time_structure.pdf
- frb_period_relation.pdf

Submission materials for arXiv/viXra/Zenodo"

echo "=== Push ==="
git push origin main

echo "=== Done ==="
