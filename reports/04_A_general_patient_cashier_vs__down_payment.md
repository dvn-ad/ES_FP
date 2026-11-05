# Pairwise comparison: General patient cashier vs Down payment

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
- Needs review: True