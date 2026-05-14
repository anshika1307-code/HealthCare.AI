# Healthcare_AI - Project reuirement and context

## what this system is -

System that lets clinicians, pharmacists, and care coordinators ask natural-language questions against a corpus of authoritative clinical documents — FDA drug labels, ADA diabetes guidelines, and JNC hypertension guidelines — and receive grounded, sourced answers.
[Currently building a prototype but in a way how production ready project should be made]
---


## Data Source -

- **Type:** Pdfs, Documents (initially for prototype)
- **Place:** within the server database
- **uantity:** 3 (initially for prototype)
- **Static or Continous change:** Continous as healthcare data keep evolving
- **Documents used in prototype:**  the metformin FDA prescribing label, the ADA Standards of Care in Diabetes 2023 (Sections 6 and 9), and the JNC 8 hypertension management guidelines.

---

## System Requirements

### User Base - 

- **Primary:** Pharmacists at health plan/PBM verifying drug appropriateness (dosing, contraindications)
- **Secondary:** Care coordinators at companies looking up clinical guidelines
- **Tertiary:** Clinical informatics teams doing protocol research
- **NOT:** Direct patient use. This system is for clinically trained professionals.
- **Concurrent users:** ~10 (internal health plan tool, not consumer-facing) [for prototype]
- **Daily ueries:** ~500 [for prototype]

### Latency -

- healthcare professionals need responses faster during consultancy
- **p50 latency** < 800ms
- **p95 latency** < 2.5s
- **p99 latency** < 5s

### Accuracy

- Accuracy should be very high as it will be used in healthcare
- Faithfulness > 0.80
- Answer Relevancy	> 0.75
- Context Precision	> 0.70

### Can model hallucinate?

**No**

- **Possible failures:**
            - wrong dosage generation
            - incorrect contraindications
            - mixing multiple guidelines
            - outdated medical advice

## Potential Solution -

- A production RAG (Retrieval-Augmented Generation) system
- not a demo, but a system with defined SLAs, observable behavior, and a CI pipeline that enforces quality before every deploy.
- Why - retrieving trusted documents, generating grounded answers, less hallucination, no llm outdated data risk, sending context to llm

## Goal Of The System

Build an AI assistant that:
- understands medical documents
- retrieves relevant information
- generates grounded responses
- evaluates answer quality
- behaves like a production healthcare system

## Risk
- Retrieve incomplete context
- hallucinate dose

## Observability Requirements (Production)
- per uery metrics - llm time, retrieval time, latency
- Dashboard - for faithfullness trend, uery volume, latency graph, error rate
- Alerts - errors increasing, latency increasing, faithfulness decreasing over time
- Drift detection - As this is a sector where data source will be evolving over time so if in comparison with new documents batch, there is a major drift.
- CI evalution gate - every code push run a curtain set of predefined uestions and answer will be compared to expecting answers, if fails (>threshold) then it blocks the deploy.
- logs- structure JSON logs without patient context(original uery)