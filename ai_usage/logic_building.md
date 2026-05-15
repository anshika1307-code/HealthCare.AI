# logic_building.md

> In this file we will keep all the prompts used to build the logic of the project and its evaluation. 

## Custom Preprocessing logic
- we have the some observations and rules for preprocessing after reading the documents in preprocessing_specs_dev.md, and specs from ai after analysing the documners as well in preprocessing_specs_ai.md. 
- we will use LLM to build the preprocessing logic based on these observations and rules.
- and will evaluate our logic for correctness.

### Prompt to LLM for Custom Preprocessing Logic
- **Model used**: Claude Sonnet 4.5
- **Tool used**: Antigravity
- **Prompt to LLM**: 
noise_analysis_report.md
preprocessing_experiment_report.md
preprocessing_spec_ai.md
preprocessing_specs_dev.md
 analyse all these documents line by line, get idea what exactly needed - plan the custom preprocessing flow and logic to address all the observations/specs made by dev and ai , we will be using metformin_fda_label.pdf, ada_standards_care_diabetes_6, ada_standards_care_diabetes_9, jnc8_guidelines_manage_hypertension_original.pdf only, note- the preprocessing specs by ai doesnot include jnc8_guidelines_manage_hypertension_original.pdf specs, it is containing some different document specs so dont mismatch it 
- **Code Generated**: -
- **Result**: ai_usage\reports\preprocessing_plan.md

### Feedbacks and improvements
- **Model used**: Claude Sonnet 4.5
- **Tool used**: Antigravity
- **Prompt to LLM**: now add these ai specs of jnc8_guidelines_manage_hypertension_original.pdf in preprocessing plan, 
my uestions - 
1. not sure that in ada_standards_care_diabetes_6.pdf & ada_standards_care_diabetes_9.pdf , the A,B,C,D,E are evidence grade or not , please can you confirm it
2. in jnc8_guidelines_manage_hypertension_original.pdf there are grades like A,B,C as i mention in example of Recommendation 1
3. Not sure that the Reference list at the end should be skipped or not
4. GLUCOPHAGE, metformin hydrochloride	metformin (with alias note) is this one is correct normalization?
5. can you tell me with what logic we will detect and expand abbreviation and with which logic we do term normalization

now answering your current uestions
1. discard ADA page 1
2. JNC flowchart we can go with your recommendation, just tell me if we want to keep it then what we should do
3. Yes — parse it programmatically as a first pass, seed abbreviation_map for JNC doc
4. Keep in metadata (evidence_grade), strip from text body if they are grades only
5. Flag via metadata (safety_flag: true) + keep text as-is. Retrieval layer will boost safety-flagged chunks
6.  Both: placeholder in text flow + separate table chunk with same metadata, linked by table_number
- **Code Generated**: -
- **Result**: ai_usage\reports\preprocessing_plan_QA.md

---

##

