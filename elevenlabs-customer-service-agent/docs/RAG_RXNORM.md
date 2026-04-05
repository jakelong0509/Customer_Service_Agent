# RxNorm Medical Coding Workflow

How medical coders work with RxNorm tables to normalize drug references from clinical documentation.

---

## 1. Core Coding Process

### Step 1: Identify Drug Reference in Clinical Notes

The coder starts from unstructured text in clinical documentation:

```
"Patient was started on Lipitor 20mg daily"
"Discharged on metformin 500mg BID"
"Given morphine 4mg IV in ER"
```

### Step 2: Understand the RxNorm Concept Hierarchy (Critical)

RxNorm organizes drugs into a **hierarchy of term types (TTY)**. This is the most important concept for a coder to understand:

```
                    ┌──────────────┐
                    │  INGREDIENT  │  (IN)  — e.g., "Atorvastatin"
                    │   Most       │         The active chemical substance
                    │  Generic     │
                    └──────┬───────┘
                           │ has_ingredient / ingredient_of
                           ▼
              ┌────────────────────────┐
              │  CLINICAL DRUG COMPONENT│  (SCDC) — e.g., "Atorvastatin 20mg"
              │  Ingredient + Strength  │
              └────────────┬───────────┘
                           │ has_dose_form / dose_form_of
                           ▼
              ┌────────────────────────┐
              │  CLINICAL DOSE FORM     │  (SCDF) — e.g., "Atorvastatin 20mg Oral Tablet"
              │  + Dose Form            │
              └────────────┬───────────┘
                           │ constitues / constituted_into
                           ▼
              ┌────────────────────────┐
              │  SEMANTIC CLINICAL DRUG │  (SCD) — e.g., "Atorvastatin 20 MG Oral Tablet"
              │  The fully specified    │         The gold standard for coding
              │  generic drug           │
              └────────────────────────┘
                           │ tradename_of / has_tradename
                           ▼
              ┌────────────────────────┐
              │  SEMANTIC BRANDED DRUG  │  (SBD) — e.g., "Lipitor 20 MG Oral Tablet"
              │  Brand name version     │
              └────────────────────────┘
```

### TTY Values Reference

| TTY | Full Name | Example | Use Case |
|-----|-----------|---------|----------|
| **IN** | Ingredient | Atorvastatin | When only the chemical is documented |
| **PIN** | Precise Ingredient | Atorvastatin calcium | More specific than IN |
| **SCDC** | Semantic Clinical Drug Component | Atorvastatin 20 MG | Ingredient + strength |
| **SCDF** | Semantic Clinical Dose Form | Atorvastatin 20 MG Oral Tablet | + dose form |
| **SCD** | Semantic Clinical Drug | Atorvastatin 20 MG Oral Tablet | Fully specified generic |
| **BN** | Brand Name | Lipitor | Brand/trade name only |
| **SBDC** | Semantic Branded Drug Component | Lipitor 20 MG | Brand + strength |
| **SBDF** | Semantic Branded Dose Form | Lipitor 20 MG Oral Tablet | Brand + strength + form |
| **SBD** | Semantic Branded Drug | Lipitor 20 MG Oral Tablet | Fully specified branded |
| **DF** | Dose Form | Oral Tablet | Just the dose form |
| **SCG** | Semantic Clinical Drug Pack | Atorvastatin 20 MG Oral Tablet Pack [30] | Packaged drugs |
| **SBDG** | Semantic Branded Drug Pack | Lipitor 20 MG Oral Tablet Pack [30] | Branded packaged drugs |

---

## 2. Table-by-Table Workflow

### Step 3: Look Up in Milvus (rxnorm_concepts collection)

RXNCONSO is stored **entirely in Milvus (Zilliz)**. Search the embedded `STR` field with scalar filtering:

```python
# Semantic search with pre-filtering by source and term type
results = milvus_client.search(
    collection_name="rxnorm_concepts",
    data=[query_embedding],          # embedded "Lipitor 20mg"
    limit=5,
    filter='sab == "RXNORM" and tty in ["SCD", "SBD"]',
    output_fields=["rxcui", "str", "tty", "sab", "code"],
)

# Results (returned directly from Milvus — no PostgreSQL hit):
# rxcui  | str                          | tty  | sab     | distance
# 617311 | Lipitor 20 MG Oral Tablet    | SBD  | RXNORM  | 0.97
# 617312 | Lipitor 30 MG Oral Tablet    | SBD  | RXNORM  | 0.82
# 617310 | Lipitor 10 MG Oral Tablet    | SBD  | RXNORM  | 0.80
```

Simple drug lookups **never touch PostgreSQL** — all fields come back from Milvus.

### Step 4: Navigate Relationships via RXNREL (PostgreSQL)

Traverse relationships in PostgreSQL to find generic equivalents, confirm ingredients, or link to different levels of specificity:

```sql
-- Find generic equivalent for branded drug rxcui = 617311
SELECT rxcui2, rela
FROM rxnorm_relationships
WHERE rxcui1 = '617311'
  AND rela = 'tradename_of';

-- Result: rxcui2 = 833671, rela = tradename_of
```

Then look up the related concept in Milvus:

```python
# Query Milvus for the related concept
results = milvus_client.query(
    collection_name="rxnorm_concepts",
    filter='rxcui == "833671" and sab == "RXNORM"',
    output_fields=["rxcui", "str", "tty"],
)
# Result: rxcui=833671, str="Atorvastatin 20 MG Oral Tablet", tty=SCD
```

#### Key Relationship Types (RELA field)

| RELA Value | Meaning | Direction | Example |
|------------|---------|-----------|---------|
| `ingredient_of` | This is an ingredient in | IN → SCD | Atorvastatin → Atorvastatin 20mg tablet |
| `has_ingredient` | Contains ingredient | SCD → IN | Atorvastatin 20mg tablet → Atorvastatin |
| `tradename_of` | Brand name of | SBD → SCD | Lipitor 20mg → Atorvastatin 20mg |
| `has_tradename` | Has brand name | SCD → SBD | Atorvastatin 20mg → Lipitor 20mg |
| `dose_form_of` | Dose form version of | SCDF → SCDC | Oral tablet form |
| `has_dose_form` | Has dose form | SCDC → SCDF | Component gets dose form |
| `constitutes` | Makes up | SCDF → SCD | Parts → whole drug |
| `constituted_into` | Made into | SCD → SCDF | Whole → parts |
| `contained_in` | Found in pack | SCD → SCG | Unit dose in pack |
| `contains` | Pack contains | SCG → SCD | Pack contains unit dose |

### Step 5: Get Attributes via RXNSAT

Retrieve NDC codes and other attributes for billing:

```sql
SELECT ATN, ATV
FROM rxnorm_attributes
WHERE RXCUI = '617311'
  AND ATN = 'NDC';

-- Results:
-- ATN  | ATV
-- NDC  | 00003071004
-- NDC  | 00003071031
```

### Step 6: Verify Semantic Type via RXNSTY

Confirm the concept is actually a drug:

```sql
SELECT TUI, STY
FROM rxnorm_semantic_types
WHERE RXCUI = '617311';

-- Result: TUI | STY
--         A1  | Pharmacologic Substance
```

### Step 7: Decode Abbreviations via RXNDOC

```sql
SELECT VALUE, EXPL
FROM rxnorm_documentation
WHERE KEY = 'TTY' AND VALUE = 'SBD';

-- Result: SBD | Semantic Branded Drug
```

---

## 3. Complete Coding Flow (Milvus + PostgreSQL)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CLINICAL NOTE INPUT                                      │
│    "Patient started on Lipitor 20mg"                        │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MILVUS SEMANTIC SEARCH (rxnorm_concepts collection)      │
│    Embed "Lipitor 20mg" → search with filter                │
│    filter='sab=="RXNORM" and tty in ["SCD","SBD"]'         │
│                                                              │
│    Returns directly (no PostgreSQL):                         │
│    rxcui=617311, str="Lipitor 20 MG Oral Tablet", tty=SBD  │
│    rxcui=617312, str="Lipitor 30 MG Oral Tablet", tty=SBD  │
│    distance: 0.97, 0.82                                     │
│                                                              │
│    ✓ Simple lookup complete — all data from Milvus          │
└─────────────────────────┬───────────────────────────────────┘
                          ▼ (only if relationships/attributes needed)
┌─────────────────────────────────────────────────────────────┐
│ 3. POSTGRESQL: RELATIONSHIP TRAVERSAL (RXNREL)              │
│    SELECT rxcui2, rela FROM rxnorm_relationships             │
│    WHERE rxcui1='617311' AND rela='tradename_of'            │
│    → rxcui2 = 833671 (Atorvastatin generic)                 │
│                                                              │
│    Then back to Milvus for concept details:                  │
│    query filter='rxcui=="833671" and sab=="RXNORM"'         │
│    → str="Atorvastatin 20 MG Oral Tablet", tty=SCD         │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. POSTGRESQL: ATTRIBUTE LOOKUP (RXNSAT)                    │
│    SELECT atn, atv FROM rxnorm_attributes                    │
│    WHERE rxcui='617311' AND atn='NDC'                       │
│    → NDC codes for billing                                  │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. OUTPUT TO CODER                                          │
│    RxCUI: 617311 (SBD) / 833671 (SCD generic)              │
│    Ingredient: Atorvastatin (301542)                        │
│    NDCs: [00003071004, ...]                                 │
│    Confidence: 97% — requires coder verification            │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Common Coding Scenarios

| Scenario | Tables Used | Strategy |
|----------|-------------|----------|
| **Simple drug lookup** | Milvus only | Semantic search with sab/tty filter — all fields returned directly |
| **Normalize brand → generic** | Milvus → PostgreSQL RXNREL → Milvus | Search STR for brand, follow `tradename_of` in RXNREL, look up result in Milvus |
| **Normalize generic → all brands** | Milvus → PostgreSQL RXNREL → Milvus | Search STR for generic, follow `has_tradename` in RXNREL, look up results in Milvus |
| **Find NDC for billing** | Milvus → PostgreSQL RXNSAT | Milvus search → rxcui → RXNSAT WHERE atn='NDC' |
| **Check drug class** | Milvus → PostgreSQL RXNSTY | Milvus search → rxcui → RXNSTY for TUI/STY classification |
| **Resolve abbreviation** | PostgreSQL RXNDOC only | Direct lookup — no Milvus needed |
| **Ingredient interaction check** | Milvus → PostgreSQL RXNREL (×2) | Navigate to IN level for both drugs via RXNREL, then check interactions |
| **Strength/dose disambiguation** | Milvus only | Filter by `tty='SCD'` in Milvus search to get exact dose forms |

---

## 5. Implementation Key Takeaways

1. **RXNCONSO lives entirely in Milvus (Zilliz)** — all 18 columns as scalar fields + STR embedded as vector. Simple drug lookups never touch PostgreSQL.

2. **TTY is the most important filter** — always know which level of the hierarchy you're targeting. Use Milvus scalar filtering: `filter='tty in ["SCD","SBD"]'`. For billing/coding, **SCD** (generic) and **SBD** (branded) are the most commonly used.

3. **Always resolve to ingredient (IN) level for interaction checking** — interactions happen at the chemical level, not the brand level. Use PostgreSQL RXNREL to navigate to IN.

4. **RXNREL (PostgreSQL) is the navigation backbone** — it's essentially a graph. The `RELA` field tells you *how* two concepts are related. Results point to rxcui values that are looked up in Milvus.

5. **RXNCONSO.STR is the entry point** — this is why we embed only this field as the vector. All searches start in Milvus, then branch to PostgreSQL tables only when relationships or attributes are needed.

6. **SAB and TTY are stored as Milvus scalar fields with indexes** — enables pre-filtering before vector search, avoiding irrelevant results from non-RXNORM sources or unwanted term types.

7. **Multiple rows per RXCUI in Milvus** — auto_id PK means every RXNCONSO row gets its own entry. Filter by `sab` and `ispref` to get the canonical representation.

---

## 6. Open Questions for Further Research

- **How does NDC-to-RxCUI mapping work for pharmacy billing?** — NDCs are 11-digit package-level codes that change frequently; RxNorm normalizes them to stable concept-level RxCUIs.
- **What is the difference between RxNorm and NHC-hosted RxNorm?** — SAB filtering matters; `RXNORM` source is the curated subset vs `MTH` (Metathesaurus) which includes UMLS mappings.
- **Should we filter out `SUPPRESS='Y'` and `LAT!='ENG'` rows before Milvus insert?** — Would reduce ~1.3M rows significantly, saving Zilliz storage cost and improving search relevance.
- **What about combination drugs?** — Drugs with multiple ingredients (e.g., "Lisinopril-Hydrochlorothiazide") use MIN (Multiple Ingredients) and have multiple `has_ingredient` relationships.
- **How does RxNorm relate to HCPCS J-codes for infusion/injectable billing?** — Separate mapping needed for professional billing of administered drugs.
- **Zilliz storage cost for ~1.3M rows with 18 scalar fields + vector?** — Need to estimate based on current Zilliz plan. May need to filter suppressed/non-English rows to fit free tier.
