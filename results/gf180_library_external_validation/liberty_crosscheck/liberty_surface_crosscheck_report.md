# Released Liberty surface cross-check

This is a partial compatibility check, not complete Liberty characterization. For each released cell variant and PVT file, nine low/mid/high slew-load points were re-simulated from the released CDL with ngspice.

- Successful point comparisons: 432.
- Overall Spearman rho: 0.9900.
- Overall Pearson r: 0.9916.
- Overall median absolute percentage error: 18.58%.
- Median SPICE-to-Liberty delay ratio: 0.814.

Absolute agreement is not assumed because the released characterization deck, waveform definitions, and parasitic assumptions are not available in the open library. Rank agreement is therefore reported separately from absolute error.
