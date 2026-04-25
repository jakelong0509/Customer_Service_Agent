## Description
Extract structured clinical entities (medications, conditions, procedures) from normalized clinical text. Output conforms to the `ExtractedEntity` schema for downstream processing.

## Normalized Clinical Text
```
{normalized_text}
```

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
- `extract_entities` - Tool to update agent state with extract entities ALWAYS CALL THIS TOOL

**Extract these fields for each medication:**
- entity_text: Full text mention (e.g., "Lipitor 20mg")
- entity_type: Must be "MEDICATION"
- entity_med_info:
  - brand_name: If mentioned (e.g., "Lipitor")
  - dose: Numeric value (e.g., "20")
  - unit: Unit of measure (e.g., "mg")
  - route: Administration route (e.g., "oral", "IV")
  - form: Drug form (e.g., "tablet", "capsule")
  - frequency: Dosing schedule (e.g., "daily", "twice daily")