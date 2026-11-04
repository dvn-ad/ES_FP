# Reference vs. many variants

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
