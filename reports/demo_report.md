# bpmndiff demo report

Dataset: `/home/mendoan/Projects/College/ES/FP/BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset`

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
- HTML: [01_A_old_vs__new_patient_registration.html](01_A_old_vs__new_patient_registration.html)

### General vs. corporate new patient registration

- Mode: A
- Models: General new patient registration, Corporate new patient registration
- Verdict: **semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 5 operations
- HTML: [02_A_general_vs__corporate_new_patient_registration.html](02_A_general_vs__corporate_new_patient_registration.html)

### General vs. corporate inpatient registration

- Mode: A
- Models: General inpatient registration, Corporate inpatient registration
- Verdict: **semantic_change**
- Trace equivalent: True
- Details: 2 operations
- HTML: [03_A_general_vs__corporate_inpatient_registration.html](03_A_general_vs__corporate_inpatient_registration.html)

### General patient cashier vs. down payment

- Mode: A
- Models: General patient cashier, Down payment
- Verdict: **semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 32 operations
- HTML: [04_A_general_patient_cashier_vs__down_payment.html](04_A_general_patient_cashier_vs__down_payment.html)

### Patient registration family

- Mode: B
- Models: General new patient registration, Corporate new patient registration, General inpatient registration, Corporate inpatient registration
- Verdict: **semantic_and_behavioral_change, semantic_and_behavioral_change, semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 12 core elements
- HTML: [05_B_patient_registration_family.html](05_B_patient_registration_family.html)

### Patient registration evolution chain

- Mode: C
- Models: Registration of old patients, General new patient registration, Corporate new patient registration
- Verdict: **semantic_and_behavioral_change -> semantic_and_behavioral_change**
- Trace equivalent: False
- Details: 0 reverts, oracle consistent=True
- HTML: [06_C_patient_registration_evolution_chain.html](06_C_patient_registration_evolution_chain.html)
