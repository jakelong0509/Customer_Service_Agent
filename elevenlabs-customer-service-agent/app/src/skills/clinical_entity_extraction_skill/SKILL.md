---
name: clinical_entity_extraction_skill
description: Extract structured clinical entities (medications, conditions, procedures) from normalized clinical text. Output conforms to the `ExtractedEntity` schema for downstream processing.
when_to_use: Use this skill after text normalization to identify and extract
  - **Medications** Drug names, doses, routes, frequencies
  - **Conditions** Confirmed diagnoses and diseases
  - **Procedures** Completed interventions and diagnostic tests
  - **Anatomical locations** Body sites mentioned
---
**Accuracy is paramount—hallucination of clinical information is strictly prohibited.**

## Core Rules

### ZERO HALLUCINATION RULE
- **NEVER invent** clinical entities not explicitly stated
- **NEVER infer** diagnoses without documented evidence
- **NEVER assume** attributes not supported by explicit text
- **NEVER normalize** values (don't add units if absent)
- **NEVER expand** clinical significance beyond documentation

### EVIDENCE ANCHORING
Every extracted entity MUST be directly verifiable from the source text.

## Extraction Categories

| Category | Extract | Do NOT Extract |
|----------|---------|----------------|
| **CONDITION** | Confirmed diseases, syndromes | Rule-outs, differentials, "possible", "suspected", "query" |
| **PROCEDURE** | Completed interventions, diagnostic tests, surgeries | Planned, cancelled, "to be scheduled" |
| **MEDICATION** | Active medications | Discontinued meds, allergies |

## Medication Extraction

Extract these fields when present:
- `drug_name`: Generic or brand name
- `dose`: Numeric amount
- `unit`: mg, mcg, units, etc.
- `route`: PO, IV, IM, SC, topical, etc.
- `frequency`: qd, BID, TID, q4h, PRN, etc.
- `duration`: x7d, x1mo, etc.

**Examples:**
| Text | Drug | Dose | Unit | Route | Frequency |
|------|------|------|------|-------|-----------|
| "Metformin 500mg PO BID" | Metformin | 500 | mg | PO | BID |
| "Lisinopril 10 mg daily" | Lisinopril | 10 | mg | PO | qd |

## Condition Extraction

Extract with:
- `condition_name`: Standard name
- `certainty`: confirmed, suspected, ruled_out
- `temporality`: current, past, future
- `is_negated`: true if "no", "denies", "without"

**Examples:**
| Text | Condition | Certainty | Negated |
|------|-----------|-----------|---------|
| "Patient has diabetes" | Diabetes | confirmed | false |
| "No history of HTN" | Hypertension | confirmed | true |
| "possible pneumonia" | Pneumonia | suspected | false |

## Available Tools
- `create_medication_entity` - Create a medication entity with all metadata
- `create_condition_entity` - Create a condition entity
- `store_entities` - Save all extracted entities to global state

## Output Format
```json
{
  "extracted_entities": [
    {
      "entity_text": "Metformin 500mg PO BID",
      "entity_type": "MEDICATION",
      "entity_metadata": {
        "is_negated": false,
        "certainty": "confirmed",
        "temporality": "current"
      },
      "entity_med_info": {
        "dose": "500",
        "unit": "mg",
        "route": "PO",
        "frequency": "BID"
      }
    }
  ]
}
```

## Example

**Input:**
```
Patient is a 55-year-old male with history of hypertension and type 2 diabetes. 
Current medications: Metformin 1000mg BID, Lisinopril 10mg daily. 
Denies any history of heart disease. Possible sleep apnea per wife's report.
```

**Output Entities:**
1. Hypertension (CONDITION, confirmed, current)
2. Type 2 Diabetes (CONDITION, confirmed, current)
3. Metformin 1000mg BID (MEDICATION, dose=1000, unit=mg, frequency=BID)
4. Lisinopril 10mg daily (MEDICATION, dose=10, unit=mg, frequency=qd)
5. Heart disease (CONDITION, negated - NOT extracted as positive)
6. Sleep apnea (NOT extracted - only "possible" per wife's report)
