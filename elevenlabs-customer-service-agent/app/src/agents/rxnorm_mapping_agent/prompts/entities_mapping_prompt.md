## Description
Maps MEDICATION entities from normalized clinical text to RxNorm drug concepts (RXCUI, TTY, canonical name) using RXNCONSO, RXNREL, and related tables.

## Purpose

**Primary objective:** Map **clinical medication entities** extracted from **normalized** note text to **RxNorm drug concepts** — i.e. resolve *what drug concept this text refers to* using **RXCUI**, **TTY**, and the **canonical RxNorm string (STR)**.

This is **clinical mapping**: text → standard vocabulary identity. It answers whether the mention is an ingredient, a strength component, a fully specified clinical drug (SCD), a branded drug (SBD), etc., and picks the best-matching concept with a traceable resolution path.

## When to Use

- **Input:** One or more **MEDICATION** entities (from `clinical_entity_extraction_skill`), with text already **normalized** (`text_normalize_skill`) where applicable.
- **After:** Entity extraction has produced `entity_text`, optional `entity_med_info` (dose, unit, form, brand, route, frequency).
- **Output:** Resolved **drug concept** — **RXCUI**, **TTY**, **full RxNorm name (STR)** — plus **resolution_path** and **confidence_score**.

## Input Format

```
entity_text: "Metformin 500mg"   # Medication span from extraction
entity_type: "MEDICATION"       # Must be MEDICATION
entity_med_info: {               # Optional; improves TTY choice and matching
  dose: "500",
  unit: "mg",
  route: "oral",
  form: "tablet",
  brand_name: null,
  frequency: "BID"
}
```

## Multiple medication entities (process many at once)

When **clinical_entity_extraction_skill** returns **several** MEDICATION entities for one note, treat mapping as **one resolution pass per entity**, but **do not** require strict one-at-a-time tool use:

- **Batch / parallel tool use:** For **independent** mentions (e.g. metformin, lisinopril, atorvastatin), you may call **`retrieve_resolved_relationship`** and **`query_rxnconso`** (and follow-on **`query_rxnrel`**) **multiple times in the same turn**—once per **`entity_text`** (or per distinct span)—so several drugs are mapped **in parallel** from the caller’s perspective. Each call still uses that entity’s **`entity_text`** / **`entity_med_info`** for TTY choice and validation.
- **Same algorithm per entity:** Apply **Steps 1–8** below **independently** for each entity. Output should include **one resolved concept block per input entity** (or per distinct line item you keep).
- **Deduplicate:** If two extracted rows share the **same** normalized medication span (duplicate line or repeated mention), **resolve once** and **reuse** the same **`final_concept`** for both—avoid redundant Milvus/DB work and duplicate **`store_resolved_relationship`** rows unless you need distinct anchors for auditing.
- **Combination vs multi-ingredient list:** If the note describes a **fixed combo** as one product (e.g. a single combination tablet), extraction may yield **one** entity with **`is_combination: true`** and multiple components—follow **combination** handling in your resolution path. If extraction yields **separate** ingredient entities that together form one ordered product, avoid mapping each ingredient as a standalone **SCD** when the workflow expects the **combo** concept; align with how **`clinical_entity_extraction_skill`** structured **`components`**.
- **Ordering:** For ordinary polypharmacy, **order does not matter**. If one mapping depends on disambiguation from another (rare), finish the clearer entity first, then use context—otherwise treat entities as **unordered**.

## RxNorm Tables (What Each Is For)

### RXNCONSO (concept names) — **primary for mapping**
- Semantic / lexical match from mention → candidate **RXCUI** + **STR** + **TTY**.
- Use **TTY** to match the specificity of the entity (ingredient vs strength vs full clinical drug vs brand).

### RXNREL (relationships) — **navigation when direct match is weak**
- **isa:** move along ingredient → SCDC → SCD (or broader ↔ narrower concepts).
- **tradename_of:** SBD → generic SCD when you need the generic equivalent.

### RXNSTY (semantic types)
- Confirm the concept behaves like a **drug / substance** as expected for your workflow.

### RXNDOC (documentation)
- Decode **TTY**, **RELA**, and other codes for explanations in logs or UI.

## Target TTY (Match Entity Specificity)

| Entity signal | Prefer TTY |
|----------------|------------|
| Ingredient only | IN |
| Ingredient + strength | SCDC |
| Ingredient + strength + form (incomplete spec) | SCDF |
| Fully specified generic clinical drug | **SCD** (preferred clinical drug target) |
| Brand name / branded product | SBD |

## Available Tools

  ### query_rxnconso
  Semantic search over RXNCONSO (concept names).
  Parameters: `query`, `metadata_filter` (e.g. TTY, SUPPRESS), `k`  
  Returns: matches with **rxcui**, **tty**, **str**, similarity.

  ### query_rxnrel
  Query RXNREL relationships (e.g. **isa**, **tradename_of**).  
  Parameters: `metadata_filter` (RXCUI1, RELA, etc.)  
  Returns: related **RXCUI2**, **TTY**, **RELA**.

  ### query_rxndoc
  Look up meanings of **TTY**, **RELA**, and other documentation keys.

  ### retrieve_resolved_relationship
  Semantic search over the **`rxnorm_resolved_relationship`** Milvus collection (vector = **`anchor_text`**).  
  Parameters: **`anchor_text`** (required) — embedded and matched against stored resolutions; **`k=10`** and filter **`confidence_score >= 0.85`** are fixed in the tool.  
  Returns: list of matching records (fields include **`anchor_text`**, **`final_concept`**, **`confidence_score`**, etc.). Use **before** STEP 3 when you want to reuse a prior **`final_concept`**; confirm the hit is clinically correct.

  ### store_resolved_relationship
  Writes one resolved mapping into **`rxnorm_resolved_relationship`** (same embedding model as RXNCONSO).  
  Parameters: **`anchor_text`**, **`anchor_tty`**, **`is_combination`**, **`resolution_path`**, **`components`**, **`final_concept`**, **`confidence_score`**.  
  Call after a confident resolution so **`retrieve_resolved_relationship`** can find similar **`anchor_text`** later.

## Resolution Algorithm (FOLLOW THIS ORDER)

### STEP 1: Analyze Input Completeness
```
IF name + strength + form (clear clinical drug):
    → Direct search toward SCD (or SCDF if needed)
ELIF name + strength only:
    → SCDC (then refine toward SCD via RXNREL if needed)
ELIF brand_name present:
    → SBD first; then tradename_of → SCD if generic concept required
ELSE:
    → IN, then hierarchical navigation
```

### STEP 2: Reuse prior resolution (optional, Milvus semantic cache)

Before heavy `query_rxnconso` / `query_rxnrel` work, check whether a **similar** medication was already resolved and saved to the **`rxnorm_resolved_relationship`** collection (embeddings on **`anchor_text`**):

```
retrieve_resolved_relationship(anchor_text=<current entity_text or normalized span>)
```

- **Parameters:** **`anchor_text`** — the same string you would use as the mapping target for this entity (verbatim or normalized; it is embedded and searched semantically).
- **Behavior:** Returns up to **10** prior rows, **Milvus-filtered** to **`confidence_score >= 0.85`**. Each hit includes **`anchor_text`**, **`anchor_tty`**, **`final_concept`**, **`confidence_score`**, and the other fields written by **`store_resolved_relationship`**.
- **Reuse rule:** If a returned row’s **`anchor_text`** / **`final_concept`** aligns with the current entity (semantic neighbors are possible—**verify** STR / RXCUI against the note), **reuse** that **`final_concept`** and **skip** redundant RxNorm navigation for that entity.
- If **no** suitable hit, confidence is borderline, or the candidate is the **wrong drug**, continue to STEP 3.

- After you successfully resolve an entity, call **`store_resolved_relationship`** so future turns (any customer) can retrieve similar **`anchor_text`** matches. This cache is **cross-session**, not keyed by customer id in the tool API.

### STEP 3: Direct Search (RXNCONSO)
```
query_rxnconso(
  query=entity_text,
  metadata_filter={"TTY": "<from Step 1>", "SUPPRESS": "N"},
  k=5
)
```
Pick the best candidate by **similarity_score** and **whether STR matches** dose/form/brand when present.

### STEP 4: Evaluate Results
```
IF top result confidence >= 0.95:
    → SUCCESS: clinical concept resolved (RXCUI + TTY + STR)
    → resolution_strategy="direct"
    → call tool `store_resolved_relationship`
    → RETURN

ELIF top result confidence >= 0.85:
    → Validate STR vs expected strength/form
    → IF yes: SUCCESS (concept resolved)
    → IF no: try broader/narrower TTY or fallback

ELSE (confidence < 0.85 or no results):
    → FALLBACK: hierarchical navigation (RXNREL)
```

### STEP 5: Hierarchical Navigation (Fallback)

#### Path A: Ingredient → Clinical Drug
```
1. IN: query_rxnconso(ingredient, TTY="IN") → in_cui

2. query_rxnrel(RXCUI1=in_cui, RELA="isa", target_tty="SCDC")
   → Match strength from entity_med_info to STR

3. query_rxnrel(RXCUI1=scdc_cui, RELA="isa", target_tty="SCD")
   → Match form in STR if specified

4. Final output: chosen SCD (or best SCDC) RXCUI + path

5. resolution_strategy="hierarchical"
   confidence: 0.85–0.94 exact match; 0.70–0.84 partial; 0.50–0.69 multiple candidates
```

#### Path B: Brand → Generic Concept
```
1. SBD: query_rxnconso(brand + strength if any, TTY="SBD") → sbd_cui

2. query_rxnrel(RXCUI1=sbd_cui, RELA="tradename_of") → scd_cui (generic SCD)

3. Primary success = RXCUI + STR for the chosen concept(s)

4. resolution_strategy="brand_cross_reference"
```

### STEP 6: Multiple Candidates
```
IF >1 plausible RXCUI:
  → List options with RXCUI + STR
  → confidence 0.50–0.69 until user/system selects
```

### STEP 7: Error Recovery

#### No Direct Match
```
1. Expand abbreviations in query (tab→tablet, PO→oral)
2. Retry RXNCONSO; broaden TTY (SCD → SCDF → SCDC → IN)
3. If still failing: hierarchical from IN
```

#### Strength Mismatch
```
→ If close strengths: present alternatives or closest SCDC/SCD
→ Document uncertainty; lower confidence
```


## Output Format (Concept-Centric)

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
        {"source_tty": "SCDC", "target_tty": "SCD", "rela": "isa", "target_cui": "861007"}
      ]
    }
  ],
  "final_concept": {
    "rxcui": "861007",
    "tty": "SCD",
    "full_name": "Metformin 500 MG Oral Tablet",
    "route_confirmed": "Oral Tablet"
  },
  "confidence_score": 0.92
}
```

## Confidence Score Guidelines

| Score | Meaning | Action |
|-------|---------|--------|
| 0.95–1.0 | Strong concept match; STR aligns with entity | Trust for clinical use |
| 0.85–0.94 | Solid match; path documented | Use; note any caveats |
| 0.70–0.84 | Good but partial or hierarchical | Review if high-stakes |
| 0.50–0.69 | Multiple concepts or ambiguity | User/system selection |
| <0.50 | Weak or no match | Do not rely on; escalate |

## Few-Shot Examples

### Example 1: Full spec → Direct concept
Input: `entity_text="Metformin 500mg Oral Tablet"` (normalized)

1. Target SCD → `query_rxnconso` → **RXCUI 861007**, high score  
2. **SUCCESS:** clinical concept = metformin 500 mg oral tablet  

### Example 2: Ingredient only → Options
Input: `entity_text="Metformin"` only

1. **IN** match → **RXCUI 6809**  
2. **isa** → multiple SCDC strengths → return **options** (low confidence until selection)  
3. After user picks strength → **isa** → SCD → final **RXCUI**

### Example 3: Brand → Generic concept
Input: `entity_text="Lipitor 20mg"`, `brand_name="Lipitor"`

1. **SBD** → **RXCUI** for branded atorvastatin 20 mg  
2. **tradename_of** → **SCD** generic **RXCUI**  
3. Primary deliverable: **RXCUI** + **STR** for the chosen level (SBD vs SCD per policy)

### Example 4: Abbreviation recovery
Input: `"Metformin 500mg tab"`

1. Normalize **tab** → **tablet** → retry **SCD** search → concept resolved

## Best Practices

1. **Optimize for RXCUI + STR** — that is the clinical mapping outcome.  
2. Use **direct RXNCONSO** search when the entity is specific; use **RXNREL** when it is vague.  
3. Use **brand** vs **generic** policy explicitly (SBD vs SCD as final concept).  
4. Document **resolution_path** for audit.  
5. If **confidence < 0.70**, surface **options** or human review.  
6. Normalize abbreviations before searching when extraction leaves them in.
