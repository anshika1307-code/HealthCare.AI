# dev_decisions_eval.md
In this Document added all my prompts used to evaluate each decision i had taken in decision.md file, with help of LLMs asking to generate the experiment on certain chooses or comparing the current decision with other approaches in the market.


## Preprocessing 
- Tool used - Antigravity
- Model used - GPT-OSS 120B (Medium)
- Dev -> for this project our first task is to evaluate each decision with proper experiment or comparing with other approaches 
lets start with preprocessing , for that first we extract the data with pdfplumber, pyMuPDF and langchain loader or any else that you feel is good - then we analyse the output and check if there is need for custom preprocessing or not. If needed prepare a preprocessing_spec_ai.md by analysing what need to be clean and how. then i will prepare it by manually looking at the documents - preprocessing_specs_dev.md . if not needed a custom then tell me what to use and why?

- Dev -> you had to evaluate the decision.md file and you are justifing your answers with the context of decision.md, that is not how you do create a seperate folder run experiment on existing data source documents then compare the actual outputs then answer.

- reuire dependencies - pip install pdfplumber pymupdf langchain langchain-community
- AI response - Experiments\Preprocessing\run_extraction_experiment.py
Documentation\preprocessing_spec_ai.md

- Dev - custom preprocessing needed or any preprocessing tool which is better (Claude Sonnet 4.6)
- AI - Experiments\Preprocessing\run_noise_analysis.py
- dependencies - python -m pip install unstructured[pdf]

- Conclusion - Current decisions are the best for current Project scope

## 