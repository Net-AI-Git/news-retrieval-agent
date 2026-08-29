# GOAL — Grade בשלושה פסקי דין עם evidence מצטבר

**Status:** Implemented — live verification failing at 9/12  
**Author:** N/A  
**Created:** 2026-08-28  
**Updated:** 2026-08-29  
**SDD(s) Impacted:** none; המשתמש אישר במפורש להמשיך ללא SDD קיים  

הקובץ הזה הוא המפרט היחיד לעבודת Grade הנוכחית. אין להשתמש בתוכניות Grade ישנות לניסוח הפרומפט.

---

## החלטת מוצר מעודכנת

פסק הדין `rewrite` בוטל.

Grade מחזיר רק:

- `enough`
- `missing_hop`
- `empty_stop`

כל CHUNK שנשלף נשמר ב-evidence. Grade אינו מוחק, מסנן או מבקש להתעלם מ-CHUNK. CHUNK שאינו מכסה צורך פשוט אינו נספר ככיסוי, אך נשאר במצב ונשלח ל-Answer בסיום.

שלושת מקרי הכיסוי שסווגו בעבר `rewrite` מסווגים מעכשיו `missing_hop`: ממשיכים לחפש את המידע החסר ושומרים את ה-CHUNK הקיים.

---

## Friend review — תיכשל אם תעשה את אלה

1. אסור להכניס לפרומפט שאלות, תשובות, כותרות, snippets, URLs, תת-שאלות או חיקויים של Q01–Q11 או של `grade_coverage.json`.
2. `grade_agent.md` נשאר מתחת ל-40 שורות ומתחת ל-350 מילים.
3. המבנה הוא `# Identity`, אחריו `# Instructions`, ו-`# Examples` אופציונלי בלבד. אין `# Context`.
4. אין תבניות `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]` או `RESPONSE FORMAT`.
5. פסקי הדין החוקיים היחידים הם `enough`, `missing_hop`, `empty_stop`.
6. `note` ריק ב-`enough` וב-`empty_stop`; ב-`missing_hop` הוא לא ריק ואינו חוזר על `prior_queries.question`.

לפני כל הרצה חיה יש לפתוח את הפרומפט, לבדוק את ששת הסעיפים ולוודא `prompt_leak_hit=0`.

---

## מודל וחוזה

**מודל:** `OPENAI_GRADE_MODEL=openai/gpt-4.1-mini`  
**קלט:** `{question, evidence, prior_queries}`  
**פלט:** `GradeResult` עם `verdict` ו-`note`  

`GradeResult.verdict` מוגבל בסכמה לשלושת הערכים החוקיים. ערך אחר אינו חלק מהחוזה.

---

## הזרימה

```text
Question
    → Gather
    → Retrieve
    → Tools      מוסיף CHUNKים ל-evidence
    → Grade      enough / missing_hop / empty_stop
        missing_hop → Gather, בלי למחוק evidence
        enough / empty_stop → Answer עם כל evidence שנצבר
```

`GroundedAnsweringState.evidence` הוא state מצטבר. כל תוצאת Tools מתווספת לרשימה הקיימת. `answer_node` מעביר את הרשימה המלאה ל-Answer; סינון citations לאחר מכן אינו מוחק evidence מהקלט של Answer.

---

## שלושת המצבים

### `enough`

כל צורכי המידע מכוסים יחד ב-evidence המצטבר. עוצרים מיד. רעש אינו מונע עצירה. `note` ריק.

### `missing_hop`

לפחות צורך אחד עדיין אינו מכוסה ויש לבצע חיפוש נוסף. זה כולל:

- צורך שטרם חופש;
- עיתון או מסנן תאריך-פרסום שטרם נוצל;
- CHUNK חלקי או לא קשור;
- CHUNK מהעיתון או מתאריך הפרסום הלא נכון;
- חפיפת מילות מפתח ללא העובדה המבוקשת.

כל evidence קיים נשמר. `note` מכוון רק לצורך או לתיקון הבא ושונה מכל שאלה קודמת.

### `empty_stop`

כל הצרכים והפילטרים הנדרשים כבר חופשו, ה-evidence המצטבר עדיין אינו מאפשר תשובה, ואין חיפוש שונה מהותית שנותר. עוצרים ושולחים את כל evidence ל-Answer. `note` ריק.

---

## כיסוי וחיפוש

- מפצלים את שאלת המשתמש לצרכים עצמאיים.
- עיתון נקשר רק לטענה שהוא אמור לדווח עליה.
- תאריך הוא פילטר רק כשהמשתמש מגביל את תאריך פרסום הכתבה.
- CHUNK מכסה צורך רק כשה-snippet מספק את המידע וה-URL או הכותרת תואמים לעיתון הקשור.
- הפרכת הנחת כן/לא מכסה את ההנחה.
- prior query נחשב לחיפוש של צורך רק כשהוא כולל את העובדה ואת העיתון/תאריכי הפרסום הנדרשים.
- CHUNK שאינו מכסה נשמר ואינו נמחק.

---

## GT ולוח

הזהב הוא `project/src/data/ground_truth/grade_coverage.json`: 12 מצבים קפואים.

| מחלקה | מספר מקרים |
|---|---:|
| `enough` | 3 |
| `missing_hop` | 6 |
| `empty_stop` | 3 |

שלושת המקרים שהומרו ל-`missing_hop` הם:

- `grade_missing_hop_keyword_overlap`
- `grade_missing_hop_wrong_outlet`
- `grade_missing_hop_off_topic_entities`

מנקד מתוך `project/`:

```text
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_grade_coverage.run_live_grade_coverage
```

אין להשתמש ב-`tests/live_grade_gt` או `tests/live_gather_gt` כציון. תוצאות וצילומי מועמדים ישנים נשארים כהיסטוריה של חוזה ארבעת פסקי הדין ואינם מקור אמת לחוזה החדש.

---

## הצלחה

`case_success=1` כאשר:

- `predicted_verdict` שווה ל-`expected_verdict`;
- `prompt_leak_hit=0`;
- `runtime_error` ריק;
- `enough` / `empty_stop`: `note` ריק;
- `missing_hop`: `note` לא ריק ואינו שווה לשאלה קודמת.

Pass הוא שני קבצי `metrics_*.csv` החדשים ביותר ברצף, אותו prompt ואותו model, עם 12/12 בכל קובץ.

---

## Scope

**Runtime:**

- `project/src/conts.py`
- `project/src/schemas/agent.py`
- `project/src/orchestration/grounded_answering_workflow.py`
- `project/src/prompts/grade_agent.md`

**GT ובדיקות:**

- `project/src/data/ground_truth/grade_coverage.json`
- `project/src/data/ground_truth/README.md`
- `project/tests/live_grade_coverage/`
- `project/tests/grounded_answering/`

**תיעוד פעיל:**

- `project/plans/gate4-grade-coverage-prompt-goal.md`
- קטע Grade ב-`project/README.md`

**מחוץ לתחום:**

- תוכן Gather, Retrieve ו-Answer;
- Q01–Q11 וה-GT שלהם;
- כלי החיפוש ו-vector stores;
- snapshots ו-CSV היסטוריים;
- מבחני Grade/Gather הישנים.

---

## Verification

1. חיפוש פעיל מוודא שאין `GRADE_VERDICT_REWRITE` או `rewrite` בחוזה runtime, בפרומפט או ב-GT החדש.
2. בדיקה דטרמיניסטית מוודאת ש-`GradeResult` דוחה `rewrite`.
3. בדיקה דטרמיניסטית מוודאת ש-Answer מקבל את כל ה-evidence, כולל CHUNK לא רלוונטי.
4. בדיקות Friend review ו-leakage עוברות.
5. לוח Grade החי עובר 12/12 פעמיים ברצף, או מדווח במדויק אם נדרש ניסוי prompt נוסף.

---

## תוצאות חיות

- `candidate_append_only_three_verdicts.md`: ‏9/12, אפס leakage, אפס שגיאות runtime.
- `candidate_three_verdict_precedence.md`: ‏8/12, אפס leakage, אפס שגיאות runtime — נשמר כהיסטוריה ולא קודם.
- שמונת הניסויים הנוספים מ-2026-08-29:

| מועמד | ציון |
|---|---:|
| `hard_missing_precedence` | 9/12 |
| `stop_before_near_miss` | 8/12 |
| `exclusive_case_order` | 9/12 |
| `evidence_only_coverage` | 9/12 |
| `silent_need_states` | 8/12 |
| `closed_empty_stop_list` | 8/12 |
| `boolean_decision_table` | 7/12 |
| `hard_stop_exceptions` | 9/12 |

כל שמונת הניסויים הסתיימו עם אפס leakage ואפס שגיאות runtime. `candidate_evidence_only_coverage.md` נשאר בפרודקשן כשובר שוויון: הוא שומר על כלל כיסוי מבוסס-snippet בלבד ואינו מחזיר `enough` ללא תשובה מפורשת ב-evidence.

לא הושג pass כפול. הגבול שנותר הוא בין `missing_hop` לבין `empty_stop` כאשר כל הצרכים כבר חופשו אך איכות ה-CHUNKים שונה.

---

## Open questions

- none
