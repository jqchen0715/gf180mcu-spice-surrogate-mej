# Reference Link and DOI Audit

Audit date: 2026-06-03

Scope: `manuscript/microelectronics_journal_references.bib` and the rebuilt
`manuscript/microelectronics_journal_submission.bbl`.

## Summary

- The stale GF180MCU custom-design documentation URL was replaced with:
  `https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_pr.git`.
- The `sm141064.ngspice` model-file reference was also redirected to the same
  primitive-library repository, while retaining the exact local PDK commit used
  by the experiments.
- No fabricated or clearly non-existent DOI/reference was found among the DOI
  entries checked against publisher, DOI-indexed, dblp, IEEE, Elsevier, MDPI,
  JMLR, Berkeley, Wisconsin, GitHub, and ngspice sources.
- No unverified repository DOI was added. The GF180MCU PDK basis is documented
  by repository URL, exact commit hash, commit URL, and source-archive URL
  instead.

## DOI Entries Checked

| BibTeX key | DOI | Status |
|---|---|---|
| `Pan_Yang_TransferLearning_2010` | `10.1109/TKDE.2009.191` | Verified against indexed metadata for the IEEE TKDE survey. |
| `Fayazi_AI_AMS_Review_2021` | `10.1109/TCSI.2021.3065332` | Verified against indexed metadata for IEEE TCAS-I. |
| `Afacan_ML_AnalogRF_Review_2021` | `10.1016/j.vlsi.2020.11.006` | Verified against indexed metadata for Integration, the VLSI Journal. |
| `Mina_ML_AnalogIC_Review_2022` | `10.3390/electronics11030435` | Verified against the MDPI article page and indexed metadata. |
| `Lyu_Bayesian_Analog_2018` | `10.1109/TCSI.2017.2768826` | Verified against IEEE/dblp-indexed metadata. |
| `Zhang_MultiFidelity_BO_DAC_2019` | `10.1145/3316781.3317765` | Verified against ACM-indexed metadata. |
| `He_Batched_MultiFidelity_BO_TCAD_2023` | `10.1109/TCAD.2022.3175241` | Verified against IEEE-indexed metadata. |
| `Klemme_CellLib_ML_DTCO_ICCAD_2020` | `10.1145/3400302.3415713` | Verified against ACM/IEEE and university-indexed metadata. |
| `Klemme_Reliability_CellLib_TCASI_2021` | `10.1109/TCSI.2021.3069664` | Verified against IEEE/university-indexed metadata. |
| `Tang_KnowledgeTransfer_CellLib_MEJO_2025` | `10.1016/j.mejo.2024.106542` | Verified against ScienceDirect and dblp metadata. |
| `Ma_GNN_CellLib_Integration_2025` | `10.1016/j.vlsi.2024.102316` | Verified against ScienceDirect and dblp metadata. |

## URL Entries Checked

| BibTeX key | URL | Status |
|---|---|---|
| `Elsevier_MicroelectronicsJournal_AimsScope` | `https://www.sciencedirect.com/journal/microelectronics-journal` | Accessible; confirms Microelectronics Journal scope page. |
| `Google_GF180MCU_PDK_GitHub` | `https://github.com/google/gf180mcu-pdk` | Accessible but archived as of 2026-04-22; retained for exact historical PDK checkout provenance. |
| `Google_GF180MCU_PDK_GitHub` | commit/archive URLs for `de3240d7529a6970437ac3344820aaae7839f215` | Retained to document the exact local PDK commit used. |
| `GF180MCU_ReadTheDocs_CustomDesign` | `https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_pr.git` | Accessible; GitHub redirects to the primitive-library repository. |
| `GF180MCU_ReadTheDocs_StdCells_7Track` | `https://gf180mcu-pdk.readthedocs.io/en/latest/digital/standard_cells/gf180mcu_fd_sc_mcu7t5v0/index.html` | Accessible; kept as documentation for the 7-track standard cells. |
| `Ngspice_Manual` | `https://ngspice.sourceforge.io/docs/ngspice-manual.pdf` | Accessible; manual identifies version 46. |
| `Ngspice_Manual` | `https://ngspice.sourceforge.io/docs.html` | Accessible; ngspice documentation portal. |
| `Nagel_Pederson_SPICE_1973` | `https://www2.eecs.berkeley.edu/Pubs/TechRpts/1973/22871.html` | Accessible; UC Berkeley technical report page. |
| `Pedregosa_ScikitLearn_2011` | `https://www.jmlr.org/papers/v12/pedregosa11a.html` | Accessible; JMLR article page. |
| `Settles_ActiveLearning_2009` | `https://minds.wisconsin.edu/handle/1793/60660` | Accessible; University of Wisconsin technical report page. |

## Remaining Notes

- The archived `google/gf180mcu-pdk` repository is not treated as invalid because
  the manuscript uses it to identify the exact historical checkout used in the
  experiments.
- The replaced custom-design primitive-library URL is now present in the rebuilt
  `.bbl`, so the PDF reference output no longer depends on the stale custom
  design ReadTheDocs analog URL.
