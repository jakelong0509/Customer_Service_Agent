---
name: rxnorm_mapping_skill
description: Maps medication entities to RxNorm codes (SCD/SBD) with NDC codes by querying the RxNorm database tables.
when_to_use: Use this skill after entity extraction to resolve medication entities to RXCUI, NDC codes, and hierarchical path documentation.
---

## Purpose
Map medication entities to RxNorm codes (RXCUI) and NDC codes for medical billing.

## When to Use
- Input: A MEDICATION entity from clinical text
- After: clinical_entity_extraction_skill has identified the drug
- Output: Resolved RXCUI with NDC codes and resolution path

## Input Format
```
entity_text: "Metformin 500mg"  # Raw medication text
entity_type: "MEDICATION"       # Must be MEDICATION
entity_med_info: {               # Optional extracted details
  dose: "500",
  unit: "mg",
  route: "PO",
  form: "tablet",
  brand_name: null,
  frequency: "BID"
}
```

## RxNorm Database Tables

### RXNCONSO (Concept Names)
Columns: RXCUI, STR (searchable), TTY, SAB, SUPPRESS
Key TTY values (from generic to specific):
- IN = Ingredient (e.g., "Metformin")
- SCDC = Component with strength (e.g., "Metformin 500mg")
- SCDF = With dose form (e.g., "Metformin 500mg Oral Tablet")
- SCD = Fully specified clinical drug (TARGET for coding)
- SBD = Branded version (e.g., "Glucophage 500mg")

### RXNREL (Relationships)
Navigate between concepts using:
- RELA="isa" : IN → SCDC → SCD (hierarchy up)
- RELA="tradename_of" : SBD → SCD (brand to generic)

### RXNSAT (Attributes)
Get NDC codes: query where ATN="NDC", get ATV as the code

## Resolution Algorithm (FOLLOW THIS ORDER)

### STEP 1: Analyze Input Completeness
```
IF entity contains (name + strength + form):
    → Try DIRECT SEARCH on SCD
ELIF entity contains (name + strength):
    → Try DIRECT SEARCH on SCDC
ELIF entity contains brand_name:
    → Try DIRECT SEARCH on SBD
ELSE (ingredient name only):
    → Try DIRECT SEARCH on IN
```

### STEP 2: Execute Direct Search
Use query_rxnconso with appropriate TTY filter:
```
query_rxnconso(
  query=entity_text,
  tty=<determined from Step 1>,
  limit=5
)
```

### STEP 3: Evaluate Results
```
IF top result confidence >= 0.95:
    → SUCCESS: Get NDC codes via query_rxnsat
    → Set resolution_strategy="direct"
    → Set confidence_score=0.95-1.0
    → RETURN result

ELIF top result confidence >= 0.85:
    → Check: Does STR contain expected strength/form?
    → IF yes: SUCCESS with note
    → IF no: Try BROADER TTY (e.g., SCDF instead of SCD)

ELSE (confidence < 0.85 or no results):
    → FALLBACK to HIERARCHICAL navigation
```

### STEP 4: Hierarchical Navigation (Fallback)

#### Path A: Ingredient → Clinical Drug
```
1. Find IN: query_rxnconso(entity.ingredient_name, TTY="IN")
   → Get in_cui

2. Navigate up: query_rxnrel(
     RXCUI1=in_cui,
     RELA="isa",
     target_tty="SCDC"
   )
   → Get list of SCDC candidates (different strengths)

3. Match strength:
   - Parse STR field of each SCDC for "{dose} {unit}"
   - Select best match
   → Get scdc_cui

4. Continue up: query_rxnrel(
     RXCUI1=scdc_cui,
     RELA="isa",
     target_tty="SCD"
   )
   → Get SCD candidates

5. Match form (if specified):
   - Filter SCD by entity.form in STR
   → Select final_scd

6. Get NDC: query_rxnsat(RXCUI=final_scd, ATN="NDC")
   → Get billing codes

7. Set resolution_strategy="hierarchical"
   Set confidence_score based on match quality:
   - Exact strength+form match: 0.85-0.94
   - Partial match: 0.70-0.84
   - Multiple candidates: 0.50-0.69
```

#### Path B: Brand Name → Generic
```
1. Find SBD: query_rxnconso(entity.brand_name, TTY="SBD")
   → Get sbd_cui

2. Cross-reference: query_rxnrel(
     RXCUI1=sbd_cui,
     RELA="tradename_of"
   )
   → Get scd_cui (generic equivalent)

3. Get NDC: query_rxnsat(RXCUI=scd_cui, ATN="NDC")

4. Set resolution_strategy="brand_cross_reference"
   Set confidence_score=0.90-0.95
```

### STEP 5: Handle Multiple Options
```
IF hierarchical navigation returns >1 valid options:
  → Create list: "Available options:"
      [1] Metformin 500mg (RXCUI: 316151)
      [2] Metformin 850mg (RXCUI: 316153)
      [3] Metformin 1000mg (RXCUI: 316155)
  → Set confidence_score=0.50-0.69 (needs selection)
  → RETURN options for user selection
```

### STEP 6: Error Recovery

#### No Direct Match Found
```
1. Normalize: Remove abbreviations ("tab"→"tablet", "PO"→"oral")
2. Retry direct search with normalized text
3. Try broader TTY:
   - If SCD failed → try SCDF
   - If SCDF failed → try SCDC
   - If SCDC failed → try IN
4. IF all direct fail → use hierarchical from IN
```

#### No NDC Codes Found
```
1. Check parent concept (SCDC of the SCD)
2. Check branded version (related SBD)
3. IF still no NDC:
   → Add warning: "No NDC available - manual lookup required"
   → Still return RXCUI (useful for clinical reference)
```

#### Strength Mismatch
```
IF input "500mg" but closest is "250mg" or "850mg":
  1. Calculate: within 20% of target?
  2. IF yes: Present as "closest available"
  3. IF no: Present multiple options
  4. Add note: "Exact strength not available, showing alternatives"
```

## Available Tools

### query_rxnconso
Semantic search in RXNCONSO table.
Parameters:
- query: string (search text)
- tty: string (filter by TTY: IN/SCDC/SCDF/SCD/SBD)
- limit: integer (default 10)
Returns: List of {RXCUI, STR, TTY, similarity_score}

### query_rxnrel
Query relationships from RXNREL table.
Parameters:
- RXCUI1: string (source concept ID)
- RELA: string (relationship: "isa", "tradename_of")
- target_tty: string (optional filter for RXCUI2 TTY)
Returns: List of {RXCUI2, TTY, RELA}

### query_rxnsat
Query attributes from RXNSAT table.
Parameters:
- RXCUI: string (concept ID)
- ATN: string (attribute name, e.g., "NDC")
Returns: List of {ATN, ATV} where ATV is the value

### query_rxndoc
Query documentation/abbreviations.
Parameters:
- KEY: string (attribute type: "TTY", "RELA", "ATN")
- VALUE: string (the code to look up)
Returns: {EXPL} human-readable explanation

### store_resolved_relationship
Save the final result.
Parameters: resolved_relationship object (see Output Format)
Returns: confirmation string

## Output Format

```json
{
  "anchor_text": "Metformin 500mg",
  "anchor_tty": "IN",
  "is_combination": false,
  "resolution_path": "IN -> SCDC -> SCD",
  "resolution_strategy": "hierarchical",
  "components": [
    {
      "ingredient_name": "Metformin",
      "in_cui": "6809",
      "strength": "500 mg",
      "scdc_cui": "316151",
      "hops": [
        {"source_tty": "IN", "target_tty": "SCDC", "rela": "isa", "target_cui": "316151"},
        {"source_tty": "SCDC", "target_tty": "SCD", "rela": "isa", "target_cui": "6809"}
      ]
    }
  ],
  "final_concept": {
    "rxcui": "6809",
    "tty": "SCD",
    "full_name": "Metformin 500 MG Oral Tablet",
    "route_confirmed": "Oral Tablet",
    "validation_metadata": [
      {"attribute_name": "NDC", "attribute_value": "0093-1074-01"}
    ]
  },
  "confidence_score": 0.92
}
```

## Confidence Score Guidelines

| Score | Meaning | Action |
|-------|---------|--------|
| 0.95-1.0 | Direct match, exact specs, NDC found | Auto-approve |
| 0.85-0.94 | Direct or hierarchical with full path | Approve with documentation |
| 0.70-0.84 | Hierarchical with good matching | Suggest review |
| 0.50-0.69 | Multiple options, best guess | Require user selection |
| <0.50 | Poor match | Escalate to human |

## Few-Shot Examples

### Example 1: Complete Spec → Direct Path
Input: `entity_text="Metformin 500mg Oral Tablet"`, has dose/unit/form

Execution:
1. Analyze: Has name+strength+form → Try SCD
2. query_rxnconso("Metformin 500mg Oral Tablet", TTY="SCD") → RXCUI 6809 (score: 0.97)
3. Score 0.97 >= 0.95 → SUCCESS
4. query_rxnsat(RXCUI="6809", ATN="NDC") → ["0093-1074-01"]
5. RETURN with confidence=0.98, strategy="direct"

### Example 2: Ingredient Only → Hierarchical Path
Input: `entity_text="Metformin"`, no details provided

Execution:
1. Analyze: Ingredient only → Try IN
2. query_rxnconso("Metformin", TTY="IN") → RXCUI 6809 (score: 1.0)
3. Score is high but need to find specific product → Hierarchical
4. query_rxnrel(RXCUI1="6809", RELA="isa", target_tty="SCDC") → [315979, 316151, 316152, 316153]
5. Parse STR: "Metformin 250mg", "Metformin 500mg", "Metformin 850mg", "Metformin 1000mg"
6. No specific dose requested → Return options with confidence=0.65
7. User selects "500mg" → Continue navigation
8. query_rxnrel(RXCUI1="316151", RELA="isa", target_tty="SCD") → RXCUI 6809
9. query_rxnsat(RXCUI="6809", ATN="NDC") → codes
10. RETURN with confidence=0.92, strategy="hierarchical"

### Example 3: Brand Name → Cross-Reference
Input: `entity_text="Lipitor 20mg"`, brand_name="Lipitor"

Execution:
1. Analyze: Has brand → Try SBD
2. query_rxnconso("Lipitor 20mg", TTY="SBD") → RXCUI 617318 (score: 0.96)
3. Score high but need generic for standard coding
4. query_rxnrel(RXCUI1="617318", RELA="tradename_of") → RXCUI 833671
5. query_rxnsat(RXCUI="833671", ATN="NDC") → ["0003-0740-13"]
6. RETURN with confidence=0.95, strategy="brand_cross_reference"

### Example 4: No Match → Error Recovery
Input: `entity_text="Metformin 500mg tab"` (abbreviation "tab")

Execution:
1. Analyze: Has name+strength+form → Try SCD
2. query_rxnconso("Metformin 500mg tab", TTY="SCD") → No results (score: 0)
3. No match → RECOVERY
4. Normalize: "tab" → "tablet"
5. query_rxnconso("Metformin 500mg tablet", TTY="SCD") → RXCUI 6809 (score: 0.96)
6. SUCCESS with normalized query

## Best Practices
1. Always try direct search first - it's fastest and highest confidence
2. Use hierarchical when input is vague or you need to show options
3. Cross-reference brands to generics for standard coding
4. Normalize abbreviations before searching (tab→tablet, PO→oral, etc.)
5. Always retrieve NDC codes from final SCD or SBD
6. If no exact strength match, show available options within 20% tolerance
7. Document the resolution path for audit trails
8. When confidence < 0.70, always present options to user
