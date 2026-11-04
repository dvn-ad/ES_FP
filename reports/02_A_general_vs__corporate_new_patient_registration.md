# Pairwise comparison: General new patient registration vs Corporate new patient registration

| Model | Format | Nodes | Flows | Source |
|---|---|---|---|---|
| Reference | xpdl | 12 | 12 | /home/mendoan/Projects/College/ES/FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/52.Mini hospital (FO).General new patient registration/Diagram 1.xpdl |
| Variant | xpdl | 13 | 13 | /home/mendoan/Projects/College/ES/FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/53.Mini hospital (FO).Corporate new patient registration/Diagram 1.xpdl |

## Edit script

| Operation | Element | Detail | Review |
|---|---|---|---|
| INSERT | Enters company informationk 1 | added task | no |
| RENAME | Wants to register a new general patient | "Wants to register a new general patient" -> "Wants to register a new corporate patient" | no |
| DELETE_FLOW | Enter the patient's address -> Selects the register button | flow removed (1x) | no |
| INSERT_FLOW | Enter the patient's address -> Enters company informationk 1 | flow added (1x) | no |
| INSERT_FLOW | Enters company informationk 1 -> Selects the register button | flow added (1x) | no |

## Behavioural verification

- Trace equivalence: **NOT EQUIVALENT**
- Method: `trace_equivalence (tau-closure + subset construction)`
- Counterexample (variant_only): `Wants to register a new general patient -> Queries District, Subdistric, Village, and Referral -> Displays a registration form -> Enters the patient's identity -> Enter the patient's address -> Enters company informationk 1 -> Selects the register button`
  - only this model can execute the differing task and still complete
- Branching bisimulation: **NOT EQUIVALENT**

## SESE fragments (38 regions)

| Region | Nodes | Behaviour | Counterexample |
|---|---|---|---|
| R02 | 2 | EQUIVALENT | (empty trace) |
| R05 | 2 | NOT EQUIVALENT | Enter the patient's address -> Enters company informationk 1 -> Selects the register button |
| R08 | 3 | EQUIVALENT | (empty trace) |

## Fusion verdict

**semantic_and_behavioral_change**

- Element verdicts: `{'unchanged': 11, 'semantic_change': 1, 'structural_change': 1}`
- Operations: `{'INSERT': 1, 'RENAME': 1, 'DELETE_FLOW': 1, 'INSERT_FLOW': 2}`
- Needs review: False