# Healthcare.AI

---

- Live Link - 
- Observability Dashboard -
- Source Documents -
- Experiments Matrics -

## Tabel of Content


---

## Project Overview

Clinical guidance engine for
pharmacists and care coordinators.

### Problem
### Solution 
### Project Reuirements 
docs\project_context.md
---

## Project Objective
- Purpose - showing production level architecture, RAG System, Thinking and process and how AI been used in way

### What all expected :

---

## Project Scope

- Prototype grade code, Production grade architecture

---

## Development Workflow
- Architecture before code [basic_architecture.md]
- Decision and trade off written before code, backed by research and evaluating different strategies results with MLflow [decision.md]
- Documented source document inspection - manual and with ai for better preprocessing of documents [preprocessing_spec_ai.md] [preprocessing_specs_dev.md]
- Designed evaluation set covering edge cases across 7 categories: chunking boundary breaks, cross-document reasoning, normalization failures, safety-critical retrieval, out-of-scope confidence gating, table-derived questions, and adversarial hallucination traps — converted to RAGAS format with CI gate blocking deploy on faithfulness < 0.80 [eval_ques_format.md] [data\evaluation\eval_ques_openai.md]
- Evaluate custom preprocessing and chunking strategy decision with experimenting source documents with other strategies, scoring using RAGAS and logged using MLflow [ai_usage\dev_decisions_eval.md] contain all prompts given to AI tool for generating code for experiments
- Implementation - Module-by-module, each prompted against spec (Spec written by me, built by AI tool). Exact prompts given to AI tool per module documented here [ai_usage\logic_building.md]
- Unit Testing - Module-by-module using AI tool. Exact prompts given to AI tool per module documented here [ai_usage\testing.md]
- Integration Testing & bug fixing
- UI specs - Wrote Healthcare.AI UX spec referencing Optum Clinical Assistant, Stanford health AI · three-pane clinical workspace design [docs\ui_requirements.md]
- UI build - using Figma make using UI specs
- RAGMetrics and Drift Detector Pseudocode, formula and specification - docs\observability_specs.md 
- Monitoring Implementation with specification using AI

---

## Architecture
docs\basic_architecture.md add mermaid daigram

---

## File structure


---

## Decisions/Trade offs
docs\decision.md
---

### Final Tech Stack

---

## Repo Setup
docs\local_setup.md 
---

## Experiments Setup
experiments folder
---

## AI tools Usage Overview
ai_usage folder
---

