---
name: text_normalize_skill
description: Transform clinical abbreviations and acronyms into fully expanded, readable text while preserving original clinical meaning. Correct spelling errors and segment notes into logical sections (HPI, Assessment/Plan, Procedures, etc.)
when_to_use: Use this skill when processing raw clinical notes that contain
  - Medical abbreviations (HTN, DM, SOB)
  - Dosage frequencies (BID, TID, QHS)
  - Route abbreviations (PO, IV, IM, SC)
  - Specialty-specific shorthand ("c/w", "p/w")
  - Institution-specific abbreviations
---

## Core Rules
1. **Preserve all clinical meaning** - Do not alter, reinterpret, or summarize
2. **Do not add new clinical information**
3. **Maintain original measurements, lab values, medications, dosages exactly**
4. **Use clear section headers** (HPI, Assessment/Plan, Procedures, etc.)
5. **Do not fabricate sections** that are not present
6. **Keep formatting clean and professional**

## Confidence Classification

| Level | Criteria | Action |
|-------|----------|--------|
| **HIGH** | Unambiguous, standard abbreviation with clear context | Auto-expand and continue |
| **MEDIUM** | Standard abbreviation but context could suggest multiple expansions | Search RAG database for historical patterns |
| **LOW** | Non-standard, ambiguous, or unknown abbreviation | Search RAG database; flag for human review if no match |

## Safety Constraints
- **NEVER expand dosage units** without verification ("U" or "u" → flag LOW confidence)
- **NEVER expand** Joint Commission "Do Not Use" list without review ("MSO4", "MgSO4")
- **PRESERVE original abbreviation** in brackets after expansion: "Hypertension [HTN]"

## Available Tools
- `store_abbreviation` - Store abbreviation expansions in long-term memory
- `retrieve_abbreviation` - Retrieve abbreviation meanings from memory
- `reflect_on_normalization` - Complete normalization and store result


## Example

**Input:**
```
Pt p/w SOB x3d, c/w COPD exacerbation. Meds: Albuterol MDI 2 puffs q4h PRN, prednisone 40mg PO qd x5d.
```

**Output:**
```
Patient presents with shortness of breath [SOB] for 3 days [x3d], consistent with [c/w] COPD exacerbation.

MEDICATIONS:
- Albuterol metered-dose inhaler [MDI] 2 puffs every 4 hours [q4h] as needed [PRN]
- Prednisone 40mg by mouth [PO] daily [qd] for 5 days [x5d]
```
