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