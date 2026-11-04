# Pairwise comparison: General inpatient registration vs Corporate inpatient registration

| Model | Format | Nodes | Flows | Source |
|---|---|---|---|---|
| Reference | xpdl | 24 | 26 | /home/mendoan/Projects/College/ES/FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/54.Mini hospital (FO).General inpatient registration/Diagram 1.xpdl |
| Variant | xpdl | 24 | 26 | /home/mendoan/Projects/College/ES/FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/55.Mini hospital (FO).Corporate inpatient registration/Diagram 1.xpdl |

## Edit script

| Operation | Element | Detail | Review |
|---|---|---|---|
| RENAME | Wants to register Inpatient for general patients | "Wants to register Inpatient for general patients" -> "Wants to register Inpatient for corporate patients" | no |
| RENAME | Displays the registration information | "Displays the registration information" -> "Risplays the registration information" | no |

## Behavioural verification

- Trace equivalence: **EQUIVALENT**
- Method: `trace_equivalence (tau-closure + subset construction)`
- Branching bisimulation: **EQUIVALENT**

## SESE fragments (100 regions)

| Region | Nodes | Behaviour | Counterexample |
|---|---|---|---|
| R18 | 3 | EQUIVALENT | (empty trace) |
| R32 | 5 | EQUIVALENT | (empty trace) |

## Fusion verdict

**semantic_change**

- Element verdicts: `{'unchanged': 22, 'non_behavioral_rename': 1, 'semantic_change': 1}`
- Operations: `{'RENAME': 2}`
- Needs review: False