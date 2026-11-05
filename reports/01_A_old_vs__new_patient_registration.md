# Pairwise comparison: Registration of old patients vs General new patient registration

| Model | Format | Nodes | Flows | Source |
|---|---|---|---|---|
| Reference | xpdl | 12 | 12 | /home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/51.Mini hospital (FO).Registration of old patients/Diagram 1.xpdl |
| Variant | xpdl | 12 | 12 | /home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/52.Mini hospital (FO).General new patient registration/Diagram 1.xpdl |

## Edit script

| Operation | Element | Detail | Review |
|---|---|---|---|
| RENAME | Reads the Patient and Insurance database | "Reads the Patient and Insurance database" -> "Enter the patient's address" | yes |
| RENAME | Enters the medical record ID | "Enters the medical record ID" -> "Enters the patient's identity" | yes |
| RENAME | Wants to register old patients | "Wants to register old patients" -> "Wants to register a new general patient" | no |
| RENAME | Displays the query result | "Displays the query result" -> "displays the registration information to a table in the form" | yes |
| DELETE_FLOW | Displays the query result -> Selects the register button | flow removed (1x) | no |
| DELETE_FLOW | Reads the Patient and Insurance database -> Displays the query result | flow removed (1x) | no |
| DELETE_FLOW | Saves the registration information -> <exclusive gateway (XOR)> | flow removed (1x) | no |
| INSERT_FLOW | Enter the patient's address -> Selects the register button | flow added (1x) | no |
| INSERT_FLOW | Saves the registration information -> displays the registration information to a table in the form | flow added (1x) | no |
| INSERT_FLOW | displays the registration information to a table in the form -> <exclusive gateway (XOR)> | flow added (1x) | no |

## Behavioural verification

- Trace equivalence: **NOT EQUIVALENT**
- Method: `trace_equivalence (tau-closure + subset construction)`
- Counterexample (reference_only): `Wants to register old patients -> Queries District, Subdistric, Village, and Referral -> Displays a registration form -> Enters the medical record ID -> Reads the Patient and Insurance database -> Displays the query result -> Selects the register button`
  - only this model can execute the differing task and still complete
- Branching bisimulation: **NOT EQUIVALENT**

## SESE fragments (46 regions)

| Region | Nodes | Behaviour | Counterexample |
|---|---|---|---|
| R08 | 3 | EQUIVALENT | (empty trace) |
| R10 | 3 | NOT EQUIVALENT | Displays the query result -> Enters the medical record ID -> Reads the Patient and Insurance database |
| R11 | 3 | EQUIVALENT | (empty trace) |
| R12 | 3 | NOT EQUIVALENT | Displays the query result -> Reads the Patient and Insurance database -> Selects the register button |
| R26 | 5 | NOT EQUIVALENT | Displays the query result -> Selects the register button |

## Fusion verdict

**semantic_and_behavioral_change**

- Element verdicts: `{'unchanged': 8, 'semantic_change': 1, 'needs_review': 3}`
- Operations: `{'RENAME': 4, 'DELETE_FLOW': 3, 'INSERT_FLOW': 3}`
- Needs review: True