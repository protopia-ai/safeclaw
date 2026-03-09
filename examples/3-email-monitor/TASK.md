# Daily Email Summary Agent

## Goal
Load the [`gog` skill](/app/skills/gog/SKILL.md) and read emails received in the last 24 hours via Gmail at protopiasafeclaw@gmail.com and generate a concise summary. 
NOTE: Gmail access authentication via `gog` is already configured for you.

## Inputs
- Gmail inbox (unread or received in last 24h)

## Steps
1. Fetch emails from Gmail received in the last 24 hours
2. Filter out newsletters, automated notifications, and mailing lists
3. Group emails by sender or topic
4. Generate a summary with:
   - Total email count
   - High-priority or action-required items (flagged explicitly)
   - Brief per-thread summary (1-2 sentences)

## Output Format
Slack message with:
- Header: "📬 Daily Email Summary — {date}"
- Section per email group with sender, subject, and 1-line summary
- Footer: total count + any flagged action items

## Constraints
- Do not include email body content verbatim
- Skip emails older than 24 hours
- Skip sent/drafts folders
- If no emails, post "No new emails today"

## Error Handling
- If Gmail auth fails, post an alert to Slack and exit
- If Slack post fails, log to stdout and retry once
- Log all runs with timestamp and email count processed