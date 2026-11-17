# US22 labelled-case evaluation

Run from the application directory using Python 3. The command accepts bare
SOC reports and saved investigation responses that contain a `report` object.

    python -m benchmarks.evaluate_labelled_cases benchmarks/examples/us22-labels.json benchmarks/examples/us22-failed-logins-report.json benchmarks/examples/us22-routine-report.json
    python -m unittest discover -s tests -p test_evaluate_labelled_cases.py

The example investigation outputs are authored fixtures. The first case
represents repeated authentication failures without evidence of a successful
login. Its report correctly includes T1110, omits the second failed-login
citation, and adds T1078. The second case represents routine activity with
an empty set of expected techniques and an empty report mapping.

Labels map case IDs to an exhaustive set of expected MITRE techniques and,
per technique, the exhaustive list of required supporting alert IDs. Write
labels independently of the evaluated result. Provide exactly one report per
labelled case. The script emits JSON to stdout and exits with an error for
invalid input. Differences are reported as evaluation results.

Technique agreement compares the expected set with candidate and supported
techniques in the report. Evidence is evaluated
per technique. Claims outside the labels and citations outside a technique's
labelled evidence are flagged for review. Expected evidence absent from an
observed mapping is reported as missing. The evaluator covers structured MITRE
claims. Semantic review of free-text conclusions requires analyst judgement.
Client accuracy evaluation requires reviewed Aligo labels.
