# Data Guardian PII Scanner

## Task

Scan files for PII and sort them into `yes-pii` or `no-pii`.

## Steps

1. List the files in `pii-scanner/data-guardian-pii-scanner/pending/`. If empty, exit.
2. Pick a subset of 10 files from the list.
3. For each selected file:
   1. Load the file content using `cat` and the file path.
   2. Analyze the content for PII:
      - **No PII**: Move the file to `pii-scanner/data-guardian-pii-scanner/no-pii/`
      - **Contains PII**: Move the file to `pii-scanner/data-guardian-pii-scanner/yes-pii/`
4. Verify each of the selected files was moved to the correct directory.
5. Output a summary markdown table with columns: **File path**, **Type of PII**, **Severity**.