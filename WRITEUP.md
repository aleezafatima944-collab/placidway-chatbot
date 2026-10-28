# Write-up

## What I would improve with another week
- **Evaluation set:** 30 to 40 questions with expected answers, and an automatic score for retrieval and for wrong prices.
- **Better retrieval:** a re-ranker, and chunks built per table row, so clinic prices are found without keyword help.
- **Scheduled refresh:** re-scrape every night and show the "last updated" time in the app.
- **Language checks:** test Arabic and Spanish properly, and add a language-aware quote form.
- **Safer storage:** save leads and the unanswered log in a database, not CSV files.
- **Rate limit handling:** retry with waiting, plus a second model as backup.

## Known limits
- Only the 7 shared pages are used. Anything else is answered with "not in the content".
- Groq free tier allows about 8,000 tokens per minute, so fast repeated questions can show a "busy" message.
- Page 7 clinic prices come from different clinics and dates. The bot shows the dates and does not claim one country is cheaper in general.
- Answer wording changes slightly between runs, even at temperature 0.
- Urdu was tested on the price question only. Arabic and Spanish were not tested.
- Anyone can press Refresh. The CSV files may be lost when the free host restarts.
- The bot can answer "included" questions from three package pages that share the same text, so it may cite more than one source.