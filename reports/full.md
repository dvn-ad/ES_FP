# bpmndiff demo report

Dataset: `/home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset`

| Scenario | Mode | Verdict | Trace equivalent | Details |
|---|---|---|---|---|
| Old vs. new patient registration | A | semantic_and_behavioral_change | no | 10 operations |
| General vs. corporate new patient registration | A | semantic_and_behavioral_change | no | 5 operations |
| General vs. corporate inpatient registration | A | semantic_change | yes | 2 operations |
| General patient cashier vs. down payment | A | semantic_and_behavioral_change | no | 32 operations |
| Patient registration family | B | semantic_and_behavioral_change, semantic_and_behavioral_change, semantic_and_behavioral_change | no | 12 core elements |
| Patient registration evolution chain | C | semantic_and_behavioral_change -> semantic_and_behavioral_change | no | 0 reverts, oracle consistent=True |

## Scenario details

### Old vs. new patient registration

- Mode: A
- Models: Registration of old patients, General new patient registration
- Verdict: **semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 10 operations
- Report: [01_A_old_vs__new_patient_registration.md](01_A_old_vs__new_patient_registration.md)

### General vs. corporate new patient registration

- Mode: A
- Models: General new patient registration, Corporate new patient registration
- Verdict: **semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 5 operations
- Report: [02_A_general_vs__corporate_new_patient_registration.md](02_A_general_vs__corporate_new_patient_registration.md)

### General vs. corporate inpatient registration

- Mode: A
- Models: General inpatient registration, Corporate inpatient registration
- Verdict: **semantic_change**
- Trace equivalent: True
- Details: 2 operations
- Report: [03_A_general_vs__corporate_inpatient_registration.md](03_A_general_vs__corporate_inpatient_registration.md)

### General patient cashier vs. down payment

- Mode: A
- Models: General patient cashier, Down payment
- Verdict: **semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 32 operations
- Report: [04_A_general_patient_cashier_vs__down_payment.md](04_A_general_patient_cashier_vs__down_payment.md)

### Patient registration family

- Mode: B
- Models: General new patient registration, Corporate new patient registration, General inpatient registration, Corporate inpatient registration
- Verdict: **semantic_and_behavioral_change, semantic_and_behavioral_change, semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 12 core elements
- Report: [05_B_patient_registration_family.md](05_B_patient_registration_family.md)

### Patient registration evolution chain

- Mode: C
- Models: Registration of old patients, General new patient registration, Corporate new patient registration
- Verdict: **semantic_and_behavioral_change -> semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 0 reverts, oracle consistent=True
- Report: [06_C_patient_registration_evolution_chain.md](06_C_patient_registration_evolution_chain.md)
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
- Needs review: True# Pairwise comparison: General new patient registration vs Corporate new patient registration

| Model | Format | Nodes | Flows | Source |
|---|---|---|---|---|
| Reference | xpdl | 12 | 12 | /home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/52.Mini hospital (FO).General new patient registration/Diagram 1.xpdl |
| Variant | xpdl | 13 | 13 | /home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/53.Mini hospital (FO).Corporate new patient registration/Diagram 1.xpdl |

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
- Needs review: False# Pairwise comparison: General inpatient registration vs Corporate inpatient registration

| Model | Format | Nodes | Flows | Source |
|---|---|---|---|---|
| Reference | xpdl | 24 | 26 | /home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/54.Mini hospital (FO).General inpatient registration/Diagram 1.xpdl |
| Variant | xpdl | 24 | 26 | /home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/55.Mini hospital (FO).Corporate inpatient registration/Diagram 1.xpdl |

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
- Needs review: False# Pairwise comparison: General patient cashier vs Down payment

| Model | Format | Nodes | Flows | Source |
|---|---|---|---|---|
| Reference | xpdl | 22 | 23 | /home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/58.Mini hospital (cashier).General patient cashier/Diagram 1.xpdl |
| Variant | xpdl | 15 | 17 | /home/mendoan/Projects/ES_FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/59.Mini hospital (cashier).Down payment/Diagram 1.xpdl |

## Edit script

| Operation | Element | Detail | Review |
|---|---|---|---|
| DELETE | Enter the medical record ID | removed task | no |
| DELETE | Displays the query results | removed task | no |
| DELETE | Chooses the type of payment | removed task | no |
| DELETE | Selects an add button | removed task | no |
| DELETE | Prints the transaction to the printer | removed task | no |
| DELETE | Reads the Transaction Master database | removed task | no |
| DELETE | Adds it to the list | removed task | no |
| DELETE | Displays a general patient payment form | removed task | no |
| DELETE | Reads the Patient and Registration Database | removed task | no |
| INSERT | <exclusive gateway (XOR)> | added exclusive gateway (XOR) | no |
| INSERT | <exclusive gateway (XOR)> | added exclusive gateway (XOR) | no |
| RENAME | Displays it to the table | "Displays it to the table" -> "Displays Down Payment transaction form" | no |
| RENAME | Saves the Transaction | "Saves the Transaction" -> "Saves the Down Payment information" | no |
| RENAME | Saves the Transaction | "Saves the Transaction" -> "Searches for patients by register number" | no |
| RENAME | Wants to make a general patient payment | "Wants to make a general patient payment" -> "Wants to make a Down Payment transaction" | no |
| RENAME | Enters the transaction code, transaction type, quantity | "Enters the transaction code, transaction type, quantity" -> "Enters Down Payment information" | yes |
| RENAME | Displays the price | "Displays the price" -> "Displays patient information" | no |
| DELETE_FLOW | <exclusive gateway (XOR)> -> <end event> | flow removed (1x) | no |
| DELETE_FLOW | <exclusive gateway (XOR)> -> Saves the Transaction | flow removed (1x) | no |
| DELETE_FLOW | Enters the transaction code, transaction type, quantity -> Displays the price | flow removed (1x) | no |
| DELETE_FLOW | Saves the Transaction -> <exclusive gateway (XOR)> | flow removed (1x) | no |
| INSERT_FLOW | <exclusive gateway (XOR)> -> <end event> | flow added (1x) | no |
| INSERT_FLOW | <exclusive gateway (XOR)> -> <exclusive gateway (XOR)> | flow added (1x) | no |
| INSERT_FLOW | <exclusive gateway (XOR)> -> <exclusive gateway (XOR)> | flow added (1x) | no |
| INSERT_FLOW | <exclusive gateway (XOR)> -> <exclusive gateway (XOR)> | flow added (1x) | no |
| INSERT_FLOW | <exclusive gateway (XOR)> -> Displays patient information | flow added (1x) | no |
| INSERT_FLOW | Displays Down Payment transaction form -> <exclusive gateway (XOR)> | flow added (1x) | no |
| INSERT_FLOW | Displays patient information -> <exclusive gateway (XOR)> | flow added (1x) | no |
| INSERT_FLOW | Enters Down Payment information -> Searches for patients by register number | flow added (1x) | no |
| INSERT_FLOW | Saves the Down Payment information -> <exclusive gateway (XOR)> | flow added (1x) | no |
| INSERT_FLOW | Searches for patients by register number -> <exclusive gateway (XOR)> | flow added (1x) | no |
| INSERT_FLOW | Wants to make a Down Payment transaction -> Displays Down Payment transaction form | flow added (1x) | no |

## Behavioural verification

- Trace equivalence: **NOT EQUIVALENT**
- Method: `trace_equivalence (tau-closure + subset construction)`
- Counterexample (reference_only): `Wants to make a general patient payment -> Displays a general patient payment form -> Enter the medical record ID -> Reads the Patient and Registration Database -> Displays the query results -> Chooses the type of payment -> Reads the Transaction Master database -> Enters the transaction code, transaction type, quantity -> Displays the price -> Adds it to the list -> Displays it to the table -> Selects an add button -> Selects a save button -> Saves the Transaction`
  - only this model can execute the differing task and still complete
- Branching bisimulation: **NOT EQUIVALENT**

## SESE fragments (79 regions)

| Region | Nodes | Behaviour | Counterexample |
|---|---|---|---|
| R08 | 2 | EQUIVALENT | (empty trace) |
| R09 | 2 | NOT EQUIVALENT | Wants to make a general patient payment |
| R55 | 13 | NOT EQUIVALENT | Displays it to the table -> Displays the price -> Enters the transaction code, transaction type, quantity |
| R60 | 14 | skipped | (empty trace) |
| R66 | 16 | NOT EQUIVALENT | Displays it to the table -> Enters the transaction code, transaction type, quantity -> Saves the Transaction -> Selects a save button -> Saves the Transaction |

## Fusion verdict

**semantic_and_behavioral_change**

- Element verdicts: `{'unchanged': 7, 'behavioral_change': 3, 'non_behavioral_rename': 1, 'semantic_change': 1, 'needs_review': 1, 'structural_change': 11}`
- Operations: `{'DELETE': 9, 'INSERT': 2, 'RENAME': 6, 'DELETE_FLOW': 4, 'INSERT_FLOW': 11}`
- Needs review: True# Reference vs. many variants

Reference: **General new patient registration**

| Variant | Verdict | Trace equivalence | Operations |
|---|---|---|---|
| Corporate new patient registration | semantic_and_behavioral_change | no | {'INSERT': 1, 'RENAME': 1, 'DELETE_FLOW': 1, 'INSERT_FLOW': 2} |
| General inpatient registration | semantic_and_behavioral_change | no | {'INSERT': 12, 'RENAME': 7, 'DELETE_FLOW': 8, 'INSERT_FLOW': 22} |
| Corporate inpatient registration | semantic_and_behavioral_change | no | {'INSERT': 12, 'RENAME': 7, 'DELETE_FLOW': 9, 'INSERT_FLOW': 23} |

## Core elements (12)

- <start event>
- Wants to register a new general patient
- Displays a registration form
- <end event>
- Enters the patient's identity
- <exclusive gateway (XOR)>
- Saves the registration information
- <exclusive gateway (XOR)>
- Selects the register button
- Queries District, Subdistric, Village, and Referral
- Enter the patient's address
- displays the registration information to a table in the form

## Variant-specific elements (0)
# Version chain

Registration of old patients → General new patient registration → Corporate new patient registration

## Consecutive steps

| Step | Transition | Verdict | Trace equiv. | Operations |
|---|---|---|---|---|
| 1 | Registration of old patients → General new patient registration | semantic_and_behavioral_change | no | {'RENAME': 4, 'DELETE_FLOW': 3, 'INSERT_FLOW': 3} |
| 2 | General new patient registration → Corporate new patient registration | semantic_and_behavioral_change | no | {'INSERT': 1, 'RENAME': 1, 'DELETE_FLOW': 1, 'INSERT_FLOW': 2} |

## Reverts (0)

_None detected._

## Transitivity oracle

- Consistent: **True**
- Discrepancies: 0