# testing.md

> In this file we will keep all the prompts used to build the logic of the test, edge cases, evaluating tests fixing bugs/ issues found during testing for preprocessing module.

## Unit Tests for Ingestion Pipeline

### Prompt for generating unit tests for Ingestion Pipeline module
- **Model used**: Claude Sonnet 4.5
- **Tool used**: Antigravity
- **Prompt to LLM**: design the unit tests for ingestion pipeline, considering edge cases, failure cases and normal cases, also make sure that it covers all the functions, classes and methods in the ingestion pipeline, also make sure that the tests are written in python and use the pytest framework, add proper comments and docstrings to the tests and also follow the coding standards and best practices.
- **Code Generated**: 

### Evaluating the test results, testing logic and fixing the issues found during testing
- **Model used**: Claude Sonnet 4.5
- **Tool used**: Antigravity
- **Prompt to LLM**: in these tests you hadnt find any issues in current ingestion pipeline or you you just ignore them all? please think deeply and reevaluate our current ingestion pipeline and let me know if you find any issues or edge cases that should be tested
- **Report**: ai_usage\reports\ingestion_bugs.md

### Testing if the issues fixed or found new ones
- **Model used**: Claude Sonnet 4.5
- **Tool used**: Antigravity
- **Prompt to LLM**: write the test case verify the bugs, and verify your test cases covering these observations from the documents itself and the pipeline are handling them correctly and while handling them dont breaking/worsing the document and chunk uality even more, use these files
preprocessing_specs_dev.md
preprocessing_spec_ai.md
preprocessing_plan_QA.md
preprocessing_plan.md
 

