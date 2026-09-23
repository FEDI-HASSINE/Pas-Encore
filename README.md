# OrbitSchedulers — IASTAM 6.0 Problem 6

**Dynamic Workload Allocation Between Space and Ground**

A discrete-event simulation framework for evaluating orchestration
strategies in orbital edge computing. Built for the IASTAM 6.0
Technical Challenge (IEEE IAS Tunisia × TUNSA), Track 3:
Orbital Computing Architecture.

## Quick Start

```bash
pip install -r requirements.txt
pytest tests/ -v
python run_sim.py --profile burst --strategy 3 --seed 42
Repository Structure
text
src/                Simulation core (SimPy, Pydantic)
src/env/            Nodes, links, radiation model, task generator
src/strategies/     S1 (AlwaysGround), S2 (AlwaysOrbital), S3 (Greedy)
src/metrics/        M_T, M_L, M_R, M_E calculator
tests/              143 unit + integration tests
scripts/            Batch experiment runner, plot generator
results/            60-run campaign CSVs + figures
paper/              IEEE double-column interim paper
config/             Experiment configuration (YAML)
Preliminary Results
60 simulation runs = 4 workload profiles × 3 strategies × 5 seeds.

Profile	S1 (Cloud)	S2 (LEO-1)	S3 (Greedy)
Burst M_T (s)	174.85 ± 5.2	564.41 ± 2.2	171.56 ± 10.5
Energy M_L	0.013	0.130	0.013
Mixed M_L	0.015	0.147	0.015
Radiation M_L	0.012	0.119	0.012
The Greedy strategy matches the Cloud baseline on makespan
(p=0.60) because Cloud-AWS dominates the topology. Full M_R
analysis for the Radiation profile is scheduled for Phase 3.

Team
OrbitSchedulers — ISIMS, University of Sfax, Tunisia

F. Hassine — Lead Architect & Writer

Y. Ben Ayed — Environment & Metrics

M. Bellaaj — Task Generator & Baselines

A. Yassin — Orchestrator & Strategies

License
MIT (see LICENSE).
