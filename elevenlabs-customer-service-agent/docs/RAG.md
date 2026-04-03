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
- pgvector embeddings of clinical notes + their codes

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

Alert: High-confidence match for meningitis - recommend lumbar puncture
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
Input: "Patient on Lipitor 20mg, new prescription for clarithromycin"

RxNORM Mapping:
- Lipitor 20mg → RxCUI: 617311 (Atorvastatin 20mg Oral Tablet)
- Clarithromycin → RxCUI: 141962

Interaction Search:
- SEVERE: Atorvastatin + Clarithromycin
- Risk: Increased myopathy/rhabdomyolysis
- Mechanism: CYP3A4 inhibition
- Recommendation: Consider azithromycin alternative

Alert Level: CRITICAL - Requires physician review before dispensing
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
1. Set up pgvector extension in PostgreSQL
2. Create embedding pipeline (OpenAI or clinical-specific model)
3. Build base RAG service class
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
- [ ] RxNORM (RXNCONSO, RXNREL)
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

### Database Schema Additions

```sql
-- Vector embeddings for clinical notes
CREATE TABLE clinical_note_embeddings (
    id SERIAL PRIMARY KEY,
    note_hash VARCHAR(64) UNIQUE,      -- De-identified
    embedding VECTOR(1536),          -- OpenAI embedding size
    icd10_codes TEXT[],                -- Associated codes
    cpt_codes TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- UMLS concept cache
CREATE TABLE umls_concepts (
    cui VARCHAR(8) PRIMARY KEY,
    concept_name TEXT,
    semantic_type VARCHAR(10),
    embedding VECTOR(1536),
    source_vocabularies TEXT[]
);

-- RxNORM concept cache  
CREATE TABLE rxnorm_concepts (
    rxcui VARCHAR(8) PRIMARY KEY,
    concept_name TEXT,
    concept_type VARCHAR(20),
    embedding VECTOR(1536)
);

-- Drug interaction cache
CREATE TABLE drug_interactions (
    id SERIAL PRIMARY KEY,
    drug1_rxcui VARCHAR(8),
    drug2_rxcui VARCHAR(8),
    severity VARCHAR(20),             -- SEVERE/MODERATE/MINOR
    description TEXT,
    mechanism TEXT
);

-- Create indexes for similarity search
CREATE INDEX ON clinical_note_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON umls_concepts USING ivfflat (embedding vector_cosine_ops);
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
2. **Install pgvector** extension in PostgreSQL
3. **Choose embedding model** (OpenAI vs clinical-specific like BioBERT)
4. **Select first use case** (recommend: medical coding)
5. **Build MVP** with single RAG pipeline

