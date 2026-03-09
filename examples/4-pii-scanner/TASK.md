# Data Guardian PII Scanner

## Task

Scan pending files for PII and categorize them.

## Steps

1. List files in `pii-scanner/data-guardian-pii-scanner/pending/`. If empty, exit.
2. For each file, read and analyze its content for PII:
   - **No PII**: Move the file to `pii-scanner/data-guardian-pii-scanner/no-pii/`
   - **Contains PII**: Move the file to `pii-scanner/data-guardian-pii-scanner/yes-pii/`
3. Verify each file was moved to the correct category directory.
4. Verify the directory `pii-scanner/data-guardian-pii-scanner/pending/` is empty after processing all files.
5. Output a markdown table with columns: **File path**, **Type of PII**, **Severity**.