# RAG (Retrieval-Augmented Generation) Features for Clinical System

This document outlines the RAG features designed for clinical/hospital use, leveraging existing medical terminology resources.

**Data Source Location**: `D:\Medical_terms_codes`
- RxNORM (drug normalization)
- UMLS (Unified Medical Language System)
- ICD-10 codes
- CPT codes
- SNOMED CT concepts

---

## 1. Clinical Note to Medical Code Conversion

**Status**: Planned  
**Priority**: HIGH

### Purpose
Convert unstructured clinical notes into standardized billing codes (ICD-10, CPT) for accurate medical coding and reimbursement.

### Features
- **Semantic Search**: Embed clinical notes and search similar previously-coded cases
- **ICD-10 Mapping**: Map clinical descriptions to diagnosis codes
- **CPT Mapping**: Map procedures to Current Procedural Terminology codes
- **Confidence Scoring**: Only suggest codes with >90% similarity threshold
- **Dual Validation**: RAG suggestion + rules-based validation
- **Source Attribution**: Link back to similar cases (de-identified)

### Example Workflow
```
Input: "Patient presents with chest pain, radiating to left arm, 
        elevated troponin, ST elevation on ECG"

RAG Output:
- Suggested ICD-10: I21.9 (Acute myocardial infarction, unspecified)
- Alternative: I21.0 (STEMI)
- Confidence: 94%
- Similar Cases: 3 prior AMI cases with same presentation
- Physician Verification: REQUIRED
```

### Data Sources
- UMLS: SNOMED CT to ICD-10 mappings
- Historical coded encounters from `D:\Medical_terms_codes`
- Milvus (Zilliz) embeddings of clinical notes + their codes

---

## 2. Symptom-to-Diagnosis Mapping

**Status**: Planned  
**Priority**: HIGH

### Purpose
Provide differential diagnosis assistance using UMLS concepts and symptom patterns.

### Features
- **UMLS Concept Mapping**: Convert symptoms to CUIs (Concept Unique Identifiers)
- **Semantic Relationships**: Leverage UMLS semantic network for symptom-disease links
- **Differential Ranking**: Rank possible diagnoses by:
  - Symptom match score
  - Patient history relevance
  - Population prevalence
  - Severity indicators
- **SNOMED CT Integration**: Use clinical terminology hierarchies
- **Confidence Thresholds**: >85% for diagnosis suggestions

### Example Workflow
```
Input Symptoms: "Fever, headache, stiff neck, photophobia"

UMLS Mapping:
- Fever → CUI: C0155626
- Headache → CUI: C0018681  
- Stiff neck → CUI: C0277797
- Photophobia → CUI: C0085633

RAG Results:
1. Bacterial meningitis (CUI: C0025289) - 85% match
2. Viral meningitis (CUI: C0085438) - 10% match
3. Subarachnoid hemorrhage (CUI: C0038525) - 5% match

Alert: High-confidence match for meningitis, recommend lumbar puncture
```

### Data Sources
- UMLS Metathesaurus (SNOMED CT, MeSH, ICD-10)
- Symptom-disease association database
- Historical diagnosis patterns

---

## 3. Drug Normalization & Interaction Checking

**Status**: Planned  
**Priority**: CRITICAL

### Purpose
Standardize drug names using RxNORM and check for dangerous interactions.

### Features
- **RxNORM Mapping**: Convert free-text drug names to RxCUIs
- **Drug Interaction RAG**: Search interaction database by RxCUI combinations
- **Generic Alternative Suggestions**: Use RxNORM "has_tradename_of" relationships
- **Allergy Cross-Reference**: Check against patient allergy list (UMLS CUIs)
- **Dosing Guidance**: Surface standard dosing from RxNORM
- **Confidence Thresholds**: >95% for interaction alerts

### Example Workflow
```
User asks: "What's the generic for Lipitor?"
Milvus search on STR embedding → returns RXCUI = 301542 (Lipitor)
Relational query on RXNREL → find ingredient relationship → RXCUI = 1000003 (Atorvastatin)

Input: "Patient on Lipitor 20mg, new prescription for clarithromycin"

RxNORM Mapping:
- Lipitor 20mg → RxCUI: 617311 (Atorvastatin 20mg Oral Tablet)
- Clarithromycin → RxCUI: 141962

Interaction Search:
- SEVERE: Atorvastatin + Clarithromycin
- Risk: Increased myopathy/rhabdomyolysis
- Mechanism: CYP3A4 inhibition
- Recommendation: Consider azithromycin alternative

Alert Level: CRITICAL, Requires physician review before dispensing
```

### Data Sources
- RxNORM (drug concepts, relationships, interactions)
- First DataBank or similar interaction database
- Patient medication history

---

## 4. Clinical Decision Support (Combined RAG)

**Status**: Planned  
**Priority**: MEDIUM

### Purpose
Integrate symptoms, drugs, and patient history for comprehensive clinical analysis.

### Features
- **Multi-Modal RAG**: Search across symptoms + drugs + history simultaneously
- **Temporal Awareness**: "Patient had similar presentation 6 months ago"
- **Contraindication Flagging**: Drug × Diagnosis × Allergy × Age
- **Evidence-Based Suggestions**: Link to clinical guidelines
- **Risk Stratification**: High/medium/low risk classification

### Example Workflow
```
Context: 65-year-old male, diabetes, hypertension
Presentation: Chest pain, shortness of breath
Current Meds: Metformin, Lisinopril

Combined RAG Analysis:
- Symptoms suggest ACS (acute coronary syndrome)
- Drug interactions: None with current meds
- Similar cases: 12 prior diabetic patients with ACS
- Outcomes: 9 underwent successful PCI
- Risk: High (age + diabetes + symptoms)
- Recommendation: Immediate ECG, troponin, cardiology consult
```

### Data Sources
- All previous RAG sources combined
- Patient longitudinal record
- Clinical guidelines (embedded)

---

## 5. Medical Documentation Templates

**Status**: Planned  
**Priority**: MEDIUM

### Purpose**: Reduce documentation burden by suggesting templates based on diagnosis.

### Features
- **Template Retrieval**: Find similar cases and their documentation
- **SOAP Note Suggestions**: Auto-populate sections
- **ICD-10 Auto-Suggestion**: Suggest codes within note context
- **Required Elements Check**: Ensure compliance documentation
- **Billing Optimization**: Suggest additional billable elements when appropriate

### Example
```
Diagnosis: Community Acquired Pneumonia

Suggested Template:
[S]: Cough, fever, productive sputum
[O]: Crackles on auscultation, infiltrate on CXR
[A]: Community Acquired Pneumonia (J18.9)
   - CURB-65 Score: [ ]
   - PSI Score: [ ]
[P]: Antibiotics per guidelines, follow-up in 48h

Required Elements:
✓ Severity documented
✓ Causative organism (if known)
✓ Treatment plan
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
1. Set up Milvus vector database
2. Create embedding pipeline (OpenAI or clinical-specific model)
3. Build base RAG service class (Milvus search → SQL lookup)
4. Connect to `D:\Medical_terms_codes` data

### Phase 2: Medical Coding (Weeks 3-4)
1. Build `convert_note_to_codes()` tool
2. Embed historical coded encounters
3. Implement ICD-10 similarity search
4. Add physician confirmation workflow

### Phase 3: Diagnosis Support (Weeks 5-6)
1. Integrate UMLS concept mapper
2. Build symptom-to-CUI pipeline
3. Implement differential diagnosis RAG
4. Add confidence thresholds

### Phase 4: Drug Safety (Weeks 7-8)
1. Build RxNORM concept mapper
2. Create drug interaction database
3. Implement interaction RAG search
4. Add allergy cross-reference

### Phase 5: Integration (Weeks 9-10)
1. Combine all RAG sources
2. Build clinical decision support UI
3. Add audit logging
4. Performance optimization

---

## Data Requirements

### From `D:\Medical_terms_codes`:
- [ ] UMLS Metathesaurus (MRCONSO, MRSTY, MRREL)
- [ ] RxNORM: Full table set:
  - [ ] RXNCONSO (Milvus/Zilliz only: all columns as scalar fields + STR embedded as vector)
  - [ ] RXNREL (PostgreSQL: concept relationships)
  - [ ] RXNSAT (PostgreSQL: attributes, NDC codes)
  - [ ] RXNSTY (PostgreSQL: semantic type classification)
  - [ ] RXNDOC (PostgreSQL: abbreviation/reference lookup)
- [ ] ICD-10-CM codes and descriptions
- [ ] CPT codes (if available)
- [ ] SNOMED CT (if available separate from UMLS)

### Additional Needed:
- [ ] Historical coded encounters (de-identified)
- [ ] Drug interaction database (First DataBank, etc.)
- [ ] Clinical guidelines (PDFs or structured)

---

## Safety & Compliance Requirements

### Critical Guardrails
1. **Physician Verification Required**
   - All coding suggestions must be confirmed
   - All diagnosis suggestions require review
   - Drug interactions must trigger alerts

2. **Confidence Thresholds**
   - Medical Codes: ≥90% similarity
   - Diagnoses: ≥85% similarity  
   - Drug Interactions: ≥95% confidence
   - Below threshold: No suggestion, escalate to human

3. **Audit Logging**
   - Log every RAG query
   - Log all suggestions made
   - Log physician acceptance/rejection
   - Timestamp and user tracking

4. **Source Attribution**
   - Every suggestion shows data source
   - Link to UMLS CUI / RxCUI
   - Reference similar cases (anonymized)
   - Show confidence score

5. **HIPAA Compliance**
   - All embeddings must be de-identified
   - PHI must never enter embedding model
   - Access controls on RAG endpoints
   - Encryption at rest and in transit

### System Prompt Addition
```
IMPORTANT CLINICAL DISCLAIMER:
All coding suggestions, diagnosis recommendations, and drug interaction 
alerts provided by RAG search are ASSISTANCE ONLY and require physician 
verification. Never auto-apply codes or diagnoses. Always confirm with 
licensed healthcare provider before clinical decisions.
```

---

## Technical Architecture

### RxNorm Tables: Relational DB vs. Vector DB Architecture

The split between relational and vector storage depends on access patterns:

| Storage Type | Use Case |
|---|---|
| **Relational DB (SQL)** | Exact lookups, joins, filtering, referential integrity, structured queries |
| **Vector DB** | Semantic/similarity search on natural language text fields |

#### RXNCONSO: Milvus (Zilliz) Only

The most important table: stored **entirely in Milvus** with all columns as scalar fields. Not duplicated in PostgreSQL.

| Storage | Columns | Rationale |
|---|---|---|
| **Milvus (Zilliz)** | `id` (INT64, auto_id PK) + all 18 RXNCONSO columns as scalar fields + `vector` (FLOAT_VECTOR from STR) | `STR` is the only free-text field, embedded as vector. All other columns stored as scalar fields for filtering and direct retrieval. Simple drug lookups never touch PostgreSQL. |

**Typical query flows:**
```
Simple lookup: Milvus only:
User asks: "What is Lipitor 20mg?"
  → Milvus semantic search with filter='sab=="RXNORM" and tty in ["SCD","SBD"]'
  → Returns rxcui, str, tty, sab, code directly, no PostgreSQL needed

Generic equivalent: Milvus → PostgreSQL:
User asks: "What's the generic for Lipitor?"
  → Milvus semantic search → returns rxcui = 617311
  → PostgreSQL: RXNREL query on rxcui1 = '617311', rela = 'tradename_of'
  → Returns: rxcui = 1000003 (Atorvastatin)
```

#### RXNREL: Relational DB Only

| Storage | Columns | Rationale |
|---|---|---|
| **Relational DB** | `RXCUI1, RXAUI1, STYPE1, REL, RXCUI2, RXAUI2, STYPE2, RELA, RUI, SRUI, SAB, SL, RG, DIR, SUPPRESS, CVF` | Purely graph/relational data: traversing "ingredient_of", "has_form", "dose_form_of" relationships. No free-text to embed. Joins on RXCUI1/RXCUI2. |

> **Tip**: If relationship traversal is heavy, consider also storing this in a graph DB (Neo4j) where `(RXCUI1)-[REL:RELA]->(RXCUI2)` maps naturally to nodes and edges.

#### RXNSAT: Relational DB Only

| Storage | Columns | Rationale |
|---|---|---|
| **Relational DB** | `RXCUI, LUI, SUI, RXAUI, STYPE, CODE, ATUI, SATUI, ATN, SAB, ATV, SUPPRESS, CVF` | Structured attribute lookups, e.g., "get NDC code (ATN='NDC') for RXCUI=xxx". ATV values are mostly codes/abbreviations, not natural language. Joins via RXCUI/RXAUI. |

#### RXNSTY: Relational DB Only

| Storage | Columns | Rationale |
|---|---|---|
| **Relational DB** | `RXCUI, TUI, STN, STY, ATUI, CVF` | Tiny classification table. Used for filtering (e.g., "only return results with STY='Pharmacologic Substance'"). Pure lookup, no semantic search needed. |

#### RXNDOC: Relational DB Only

| Storage | Columns | Rationale |
|---|---|---|
| **Relational DB** | `KEY, VALUE, TYPE, EXPL` | Small reference/lookup table. Used to decode abbreviations (e.g., TTY='SCD' → "Semantic Clinical Drug"). No semantic search needed. |

#### Summary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Milvus / Zilliz (Vector DB)                   │
│                                                                 │
│  Collection: rxnorm_concepts (RXNCONSO, full table)            │
│    id (INT64, auto_id, PK)                                      │
│    rxcui, rxaui, lui, sui, sab, tty, code, str, lat, ts,       │
│    stt, ispref, saui, scui, sdui, srl, suppress, cvf           │
│    vector (FLOAT_VECTOR, dim=1536) - embedded STR field         │
│                                                                 │
│  Collection: umls_vectors                                       │
│    cui (VARCHAR, PK) + vector (FLOAT_VECTOR)                    │
│                                                                 │
│  Collection: clinical_note_vectors                              │
│    note_hash (VARCHAR, PK) + vector (FLOAT_VECTOR)              │
│                                                                 │
│  Simple drug lookups return all fields directly from Milvus.    │
│  Only relationship/attribute queries need PostgreSQL.           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ rxcui (join key for relationships/attributes)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Relational DB (PostgreSQL)                    │
│                                                                 │
│  RXNREL  (concept relationships) - brand↔generic, ingredient   │
│  RXNSAT  (attributes, NDC codes) - billing lookups              │
│  RXNSTY  (semantic types) - drug classification                 │
│  RXNDOC  (abbreviation lookup) - decode SAB, TTY, etc.         │
│                                                                 │
│  umls_concepts, clinical_note_embeddings (no vectors)           │
│  drug_interactions                                              │
└─────────────────────────────────────────────────────────────────┘
```

#### Key Design Decisions

| Decision | Recommendation |
|---|---|
| RXNCONSO storage | **Milvus (Zilliz) only**: full table with all 18 columns as scalar fields + STR embedded as vector. Not stored in PostgreSQL. |
| PK strategy | `auto_id=True` (INT64): Milvus generates PK. `rxcui` stored as regular scalar column for joining to PostgreSQL tables. |
| Only text to embed? | `RXNCONSO.STR`: the only column with natural language suitable for semantic search |
| Primary join key | `RXCUI`: links Milvus results to RXNREL ↔ RXNSAT ↔ RXNSTY in PostgreSQL |
| Pre-filtering in Milvus | `SAB, TTY` stored as scalar fields with indexes, filter before search (e.g., `sab=="RXNORM" and tty in ["SCD","SBD"]`) |
| Other RxNorm tables | **PostgreSQL only**: RXNREL, RXNSAT, RXNSTY, RXNDOC have no text to embed |
| RXNREL as graph? | If the agent does multi-hop relationship traversal (ingredient → clinical drug → branded drug), a graph DB would outperform SQL for path queries |

---

### New Components

```
app/
├── src/
│   ├── services/
│   │   ├── clinical_rag.py          # Core RAG engine
│   │   ├── medical_coding.py        # ICD-10/CPT suggestions
│   │   ├── umls_mapper.py           # UMLS concept mapping
│   │   ├── rxnorm_service.py        # RxNORM integration
│   │   ├── drug_interaction.py      # Interaction checking
│   │   └── embeddings.py            # Vector embedding service
│   │
│   ├── DAL/                         # Data Access Layer
│   │   ├── umlsDA.py               # UMLS database access
│   │   ├── rxnormDA.py             # RxNORM database access
│   │   └── medical_codeDA.py       # Code history access
│   │
│   └── skills/
│       └── clinical_rag_skill/      # New skill
│           ├── SKILL.md
│           └── scripts/
│               └── tools.py
│                   ├── search_umls_concepts()
│                   ├── search_rxnorm_drugs()
│                   ├── convert_note_to_codes()
│                   ├── check_drug_interactions()
│                   └── search_similar_cases()
│
├── data/                           # Medical data from D:\Medical_terms_codes
│   ├── umls/
│   ├── rxnorm/
│   └── embeddings/
│
└── docs/
    └── RAG.md                      # This file
```

### Milvus Vector Collections (Zilliz Cloud)

```
RXNCONSO is stored entirely in Milvus: all 18 columns as scalar fields plus the
embedded STR vector. Simple drug lookups return all data directly from Milvus
without touching PostgreSQL.

PK strategy: auto_id (INT64) - Milvus generates the PK. rxcui is a regular scalar
column used as the join key to PostgreSQL tables (RXNREL, RXNSAT, RXNSTY).

Query flows:
  Simple lookup:  Milvus search (filtered by sab/tty) → all fields returned directly
  Generic↔brand:  Milvus → rxcui → PostgreSQL RXNREL → related rxcui → Milvus lookup
  NDC billing:    Milvus → rxcui → PostgreSQL RXNSAT
  Drug class:     Milvus → rxcui → PostgreSQL RXNSTY
```

```python
from pymilvus import MilvusClient, DataType

# ─── Collection: rxnorm_concepts (full RXNCONSO table) ───
def create_rxnorm_collection(client: MilvusClient, collection_name: str = "rxnorm_concepts"):
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    schema = client.create_schema(auto_id=True, enable_dynamic_field=False)

    schema.add_field(field_name="id",       datatype=DataType.INT64,       is_primary=True, auto_id=True)
    schema.add_field(field_name="rxcui",    datatype=DataType.VARCHAR,     max_length=8)
    schema.add_field(field_name="rxaui",    datatype=DataType.VARCHAR,     max_length=8)
    schema.add_field(field_name="lui",      datatype=DataType.VARCHAR,     max_length=8)
    schema.add_field(field_name="sui",      datatype=DataType.VARCHAR,     max_length=8)
    schema.add_field(field_name="sab",      datatype=DataType.VARCHAR,     max_length=20)
    schema.add_field(field_name="tty",      datatype=DataType.VARCHAR,     max_length=10)
    schema.add_field(field_name="code",     datatype=DataType.VARCHAR,     max_length=20)
    schema.add_field(field_name="str",      datatype=DataType.VARCHAR,     max_length=500)
    schema.add_field(field_name="lat",      datatype=DataType.VARCHAR,     max_length=3)
    schema.add_field(field_name="ts",       datatype=DataType.VARCHAR,     max_length=1)
    schema.add_field(field_name="stt",      datatype=DataType.VARCHAR,     max_length=3)
    schema.add_field(field_name="ispref",   datatype=DataType.VARCHAR,     max_length=1)
    schema.add_field(field_name="saui",     datatype=DataType.VARCHAR,     max_length=20)
    schema.add_field(field_name="scui",     datatype=DataType.VARCHAR,     max_length=20)
    schema.add_field(field_name="sdui",     datatype=DataType.VARCHAR,     max_length=20)
    schema.add_field(field_name="srl",      datatype=DataType.VARCHAR,     max_length=10)
    schema.add_field(field_name="suppress", datatype=DataType.VARCHAR,     max_length=1)
    schema.add_field(field_name="cvf",      datatype=DataType.VARCHAR,     max_length=10)
    schema.add_field(field_name="vector",   datatype=DataType.FLOAT_VECTOR, dim=1536)

    index_params = client.prepare_index_params()
    index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
    index_params.add_index(field_name="rxcui")
    index_params.add_index(field_name="sab")
    index_params.add_index(field_name="tty")
    index_params.add_index(field_name="str")

    client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)


# ─── Collection: umls_vectors ───
def create_umls_collection(client: MilvusClient, collection_name: str = "umls_vectors"):
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(field_name="cui",       datatype=DataType.VARCHAR,     max_length=8, is_primary=True)
    schema.add_field(field_name="vector",    datatype=DataType.FLOAT_VECTOR, dim=1536)

    index_params = client.prepare_index_params()
    index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")

    client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)


# ─── Collection: clinical_note_vectors ───
def create_clinical_note_collection(client: MilvusClient, collection_name: str = "clinical_note_vectors"):
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(field_name="note_hash", datatype=DataType.VARCHAR,     max_length=64, is_primary=True)
    schema.add_field(field_name="vector",    datatype=DataType.FLOAT_VECTOR, dim=1536)

    index_params = client.prepare_index_params()
    index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")

    client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)
```

### Relational DB Schema (PostgreSQL: RXNCONSO removed, stored in Milvus)

```sql
-- RXNCONSO is stored entirely in Milvus (Zilliz). Not in PostgreSQL.
-- The following tables are PostgreSQL-only (no vectors, pure relational).

-- Clinical note metadata (vectors stored in Milvus: clinical_note_vectors)
CREATE TABLE clinical_note_embeddings (
    id SERIAL PRIMARY KEY,
    note_hash VARCHAR(64) UNIQUE,
    icd10_codes TEXT[],
    cpt_codes TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- UMLS concept cache (vectors stored in Milvus: umls_vectors)
CREATE TABLE umls_concepts (
    cui VARCHAR(8) PRIMARY KEY,
    concept_name TEXT,
    semantic_type VARCHAR(10),
    source_vocabularies TEXT[]
);

-- RXNREL: relational only
CREATE TABLE rxnorm_relationships (
    rxcui1 VARCHAR(8),
    rxaui1 VARCHAR(8),
    stype1 VARCHAR(10),
    rel VARCHAR(10),
    rxcui2 VARCHAR(8),
    rxaui2 VARCHAR(8),
    stype2 VARCHAR(10),
    rela VARCHAR(50),
    rui VARCHAR(12) PRIMARY KEY,
    srui VARCHAR(12),
    sab VARCHAR(20),
    sl VARCHAR(50),
    rg VARCHAR(12),
    dir VARCHAR(1),
    suppress VARCHAR(1),
    cvf VARCHAR(10)
);

-- RXNSAT: relational only
CREATE TABLE rxnorm_attributes (
    rxcui VARCHAR(8),
    lui VARCHAR(8),
    sui VARCHAR(8),
    rxaui VARCHAR(8),
    stype VARCHAR(10),
    code VARCHAR(20),
    atui VARCHAR(12) PRIMARY KEY,
    satui VARCHAR(12),
    atn VARCHAR(50),
    sab VARCHAR(20),
    atv TEXT,
    suppress VARCHAR(1),
    cvf VARCHAR(10)
);

-- RXNSTY: relational only
CREATE TABLE rxnorm_semantic_types (
    rxcui VARCHAR(8),
    tui VARCHAR(10),
    stn VARCHAR(30),
    sty VARCHAR(100),
    atui VARCHAR(12) PRIMARY KEY,
    cvf VARCHAR(10)
);

-- RXNDOC: relational only
CREATE TABLE rxnorm_documentation (
    key_val VARCHAR(100),
    value_val TEXT,
    type_val VARCHAR(10),
    expl TEXT
);

-- Drug interaction cache
CREATE TABLE drug_interactions (
    id SERIAL PRIMARY KEY,
    drug1_rxcui VARCHAR(8),
    drug2_rxcui VARCHAR(8),
    severity VARCHAR(20),
    description TEXT,
    mechanism TEXT
);

-- Relational indexes (rxnorm_concepts NOT in PostgreSQL: lives in Milvus)
CREATE INDEX ON rxnorm_relationships (rxcui1);
CREATE INDEX ON rxnorm_relationships (rxcui2);
CREATE INDEX ON rxnorm_relationships (rel);
CREATE INDEX ON rxnorm_relationships (rela);
CREATE INDEX ON rxnorm_attributes (rxcui);
CREATE INDEX ON rxnorm_attributes (atn);
CREATE INDEX ON rxnorm_semantic_types (rxcui);
```

---

## Success Metrics

### Phase 1 (Coding)
- [ ] 90%+ physician acceptance rate for code suggestions
- [ ] <2 second query latency
- [ ] 50% reduction in coding time

### Phase 2 (Diagnosis)
- [ ] Top-3 diagnosis contains correct answer 85% of time
- [ ] No missed critical diagnoses (false negatives)
- [ ] <3 second differential generation

### Phase 3 (Drug Safety)
- [ ] 100% of severe interactions flagged
- [ ] <1% false positive rate on interactions
- [ ] Zero medication errors due to missed interactions

---

## Next Steps

1. **Verify data access** to `D:\Medical_terms_codes`
2. **Set up Milvus** vector database
3. **Choose embedding model** (OpenAI vs clinical-specific like BioBERT)
4. **Select first use case** (recommend: medical coding)
5. **Build MVP** with single RAG pipeline (Milvus → SQL join)

