# GOAL — Gather שליפת כל קטעי הזהב 11/11 מול Retrieve הקפוא, בלי leakage

**Status:** In Progress  
**Author:** N/A  
**Created:** 2026-08-28  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/gather_agent.md`

זה הקובץ **היחיד** שאתה קורא. אל תקרא תוכניות אחרות. אל תעתיק תבניות פרומפט ישנות. אל תריץ לוחות חיים אחרים בתור הציון שלך.

אין לך קונטקסט אחר. כל מה שאתה צריך נמצא כאן. הצלחה = **11/11 פעמיים** על **קטעי ה-facts של ה-GT** בבאצ' החיפוש הראשון, **בלי data leakage**, עם **`# Examples` סינטטי חובה**. **אין כלל עצירה.** Leakage פוסל את **הריצה**, לא את המשימה.

**הפרומפט היחיד שמותר לערוך הוא `project/src/prompts/gather_agent.md`.**  
**אסור בשום פנים ואופן לגעת בפרומפט של Retrieve** (`project/src/prompts/retrieve_agent.md`) — לא עריכה, לא «תיקון קטן», לא מועמד ניסוי, לא העתקה לפרודקשן, לא שינוי `tool_choice`, לא באצ' במקום הופים מבודדים. Gather משתנה **לפי** Retrieve, לא להפך.

---

## Friend review — על אלה תיכשל

1. **Leakage זה רמאות.** אסור לשים בפרומפט (`gather_agent.md`) שאלות ממערכת ההערכה, תשובות, כותרות מאמרים, קטעי `facts` / `citations`, כתובות URL, תת-שאלות זהב, מחרוזות `question` של כלי, או «אותה שאלה עם שמות מזויפים». אם חומר הלימוד מכיל את המבחן, הציון לא תקף גם ב-11/11.
2. **`# Examples` חובה — רק סינטטי.** אסור פרומפט בלי סעיף `# Examples`. לפחות שני זוגות `<user_query>` / `<assistant_response>` בדומיין בדוי. אם אחרי הסתרת שמות עצם הדוגמה עדיין נראית כמו Q01–Q11 — מחק את הזוג וכתוב אחר. לא למחוק את כל הסעיף.
3. **אורך מותר.** תקרת רכות: עד **120 שורות** ו-**1200 מילים**. אם עברת — לקצר כפילויות, לא למחוק `# Examples`.
4. **מבנה ספק בלבד.** Gather רץ על `openai/gpt-4.1` (`OPENAI_GATHER_MODEL`). Retrieve / Grade / Answer נשארים על `OPENAI_MODEL` (`openai/gpt-4o-mini`). מתווה Gather:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (**חובה**, לפחות שני זוגות סינטטיים)
   - **אסור** `# Context` בקובץ. ה-JSON בזמן ריצה נשלח כהודעת user.
5. **בלי תבנית ישנה.** אל תשאיר `[INSTRUCTIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, או תגי XML בסגנון Claude כמתווה ראשי.
6. **הניסוח חופשי מול GT, כפוף ל-Retrieve.** אל תנסה להתאים מילה במילה ל-`sub_questions` או ל-`expected_tool_calls.arguments.question`. זה **לא** היעד. להעתיק אותן זה leakage. תת-שאלה ש-Retrieve יכול להעתיק ושולפת את קטע הזהב — עוברת גם אם המילים שונות מה-GT. תת-שאלה ש-Retrieve לא יכול למלא ממנה `source` / תאריך, או ש-Top-1 שלה לא הקטע — נכשלת.

אחרי כל עריכה, לפני הרצה: פתח את `gather_agent.md` ווודא שכל ששת הסעיפים עוברים. וודא ש-`retrieve_agent.md` **לא** השתנה (`git diff` עליו חייב להיות ריק).

---

## חוזה Retrieve (קפוא — Gather נכתב בשבילו)

Retrieve **כבר סגור**: 11/11 פעמיים על הופי GT מוכנים (`tests/live_retrieve_gt`, `metrics_2026-08-28_18-12-29.csv` + `18-18-29`). הקוד קורא `run_retrieve` **פעם אחת לכל מחרוזת**, עם `tool_choice="search_facts"`. כל קריאה רואה **רק** את המחרוזת הזו כהודעת user. אין שאלת אב. אין אחים. אין רשימה.

הפרומפט הקפוא עושה בדיוק את זה, בסדר הזה:

1. **`question`** = כל הודעת ה-user **מילה במילה**. בלי מחיקה, תוספת, שינוי סדר, ניסוח מחדש, או שינוי אותיות.
2. **`source`** = רק אם **באותה מחרוזת** מופיע שם עיתון מפורש; מעתיק רק את שם העיתון כמו שהוא. עיתון נספר גם בייחוס / reporting / coverage / article. אסור אדם, חברה, מוצר, נושא, או תווית כללית. **אם אין עיתון במחרוזת — `source` ריק.** Retrieve לא ישלים עיתון משאלת האב או מאח.
3. **תאריכי פרסום** = רק חלון **פרסום מאמר** מפורש באותה מחרוזת → `published_from` / `published_to` ליום ISO עם offset (`T00:00:00+00:00` … `T23:59:59+00:00`). תאריך **אירוע** נשאר ב-`question` ולא הופך לפילטר. בלי חלון במחרוזת — אין תאריכים.
4. קריאת `search_facts` **אחת**. Chroma מחזיר **Top-1** (`RETRIEVAL_TOP_K=1`).

### מה זה מחייב מ-Gather

כל מחרוזת שאתה פולט **היא** הודעת ה-user של Retrieve. אם המחרוזת לא מכילה את מה ש-Retrieve יודע לחלץ — זה אבוד. Gather לא ממלא `source`. Gather לא קורא לכלים. Gather לא «מתקן» אחרי Retrieve.

| אם Gather כותב… | Retrieve הקפוא עושה… | הקטע |
|---|---|---|
| שני עיתונים במחרוזת אחת | `source` ריק | בדרך כלל מאמר זר ב-Top-1 |
| עיתון חסר מהמחרוזת (גם אם הוא בשאלת האב) | `source` ריק | אותו כשל |
| עיתון על הטענה הלא נכונה | `source` על החיפוש הלא נכון | קטע זהב של אח נפקד |
| חלון פרסום חסר מהמחרוזת | בלי פילטר תאריך | Q08 נכשל |
| שתי טענות / שני מאמרים במחרוזת אחת | חיפוש אחד, Top-1 אחד | קטע אחד נפקד |
| הופ featured-in / name-only / השוואה שלישית | חיפוש חסר-תועלת | slot מבוזבז, זהב נפקד |
| אותם שמות עצם בשתי מחרוזות מאותו עיתון | שני Top-1 עלולים להיות אותו מאמר | המאמר השני נפקד |
| יכולת של מאמר A עם עיתון של מאמר B | `source` של B, הטמעה של A | קטע A נפקד |

**ניסוי באצ' (קריאת Retrieve אחת על כל הרשימה) נכשל: 8/11** מול 10/11 בהופים מבודדים. אל תחזור עליו. אל תבנה לוח `live_gather_retrieve_once` כציון. הייצור הוא הוף מבודד; Gather חייב לעבוד איתו.

---

## מה המוצר הזה

השירות עונה על שאלות עובדות-חדשות מעל אינדקס מאמרים **מקומי**. לולאה חיה:

```text
שאלת משתמש
    → Gather     (אתה)     רשימת תת-שאלות עצמאיות. אין כלים.
    → Retrieve   (קפוא)    לולאה: מחרוזת אחת → search_facts אחד. מעתיק question, ממלא source / תאריכים מהמחרוזת בלבד.
    → Tools      (קוד)     מריץ search_facts מול Chroma. קטע Top-1 לכל קריאה. RETRIEVAL_TOP_K=1.
    → Grade      (קפוא, מחוץ ללוח)    enough / rewrite / missing_hop / empty_stop
    → Answer     (קפוא, מחוץ ללוח)
```

הלוח הזה עוצר אחרי **באצ' הכלים הראשון**. אין Grade. אין תור Gather שני. אין Answer.

**קטע זהב = רשומה ב-`facts` של קובץ ה-GT** (`url` + משפט `fact`). הציון דורש ששניהם יופיעו ב-evidence של הבאצ' הראשון.

---

## מה Gather הוא (המשימה היחידה שלך)

לקחת את שאלת המשתמש ולפרק אותה לרשימת תת-שאלות שכל אחת היא **הודעת Retrieve אחת**: חיפוש אחד שיכול להחזיר **קטע זהב אחד**, עם עיתון וחלון פרסום **בתוך** המחרוזת כשהמשתמש נקב בהם.

Gather **לא** מחפש. Gather **לא** ממלא `source`. Gather **לא** עונה. Gather **לא** קורא לכלים. Gather **לא** משנה את Retrieve.

### קלט (כבר נשלח כהודעת user — אל תכתוב את ה-JSON הזה בפרומפט)

```json
{"question": "<שאלת המשתמש>", "prior_queries": [], "grade_note": ""}
```

הציון הוא תור ראשון: `prior_queries` ריק, `grade_note` ריק.

### פלט (כבר קשור בקוד)

```text
sub_questions: list[str]
```

אין כלים. אין שדות אחרים.

### איך לפצל כדי ש-Retrieve יביא את הקטעים (הרגלים, לא שורות מבחן)

למד את אלה בפרומפט. אל תזכיר מזהי שאלות בפרומפט. כל כלל כאן הוא **כדי ש-Retrieve הקפוא יוכל להעתיק ולמלא**.

- צד בהשוואה, יכולת ברשימה, אירוע, צד ב-`and` / `or`, צד ב-`before` / `after`, אירוע עם תאריך פרסום נפרד — כל אחד **מחרוזת משלו**, כי Top-1 מחזיר קטע אחד לקריאה.
- **אל** תוסיף הופ שלישי להשוואה עצמה («האם A קרה לפני B?») אחרי שני הצדדים — Retrieve יבזבז קריאה ולא ישלוף זהב.
- אם המשתמש שם **עיתון על טענה**, העיתון חייב להיות **בתוך** מחרוזת הטענה, כדי ש-Retrieve ימלא `source`. בלי `source`, Chroma מערבב מאמרים מכל העיתונים.
- עיתון רק על הטענה ששמה אותו. לא על אחים. Retrieve לא יעביר עיתון מאח.
- אם אותו עיתון על שתי טענות — העיתון **בשתי** המחרוזות. שני מאמרים מאותו עיתון דורשים שתי מחרוזות עם שמות עצם שונים, אחרת שני ה-Top-1 עלולים להיות אותו מאמר.
- חלון **פרסום** שהמשתמש נקב בו נשאר בטקסט התת-שאלה. Retrieve ימלא ISO. תאריך אירוע נשאר בטקסט גם הוא (Retrieve לא יהפוך אותו לפילטר — וזה רצוי).
- אסור לארוז שני עיתונים במחרוזת אחת — Retrieve ישאיר `source` ריק.
- אסור הופ שכל תפקידו «האם העיתון featured את הנושא».
- יכולות: אם שלוש+ יכולות ברשימה, שתי מחרוזות (ראשונה לחוד, השאר ביחד) **רק אם** שתי המחרוזות נושאות את **אותו** עיתון ראשון. אירוע שאינו יכולת (יום שנה, פתיחה) הולך לעיתון השני **בלבד**. אל תחליף עיתונים. אל תכפיל את האירוע גם על העיתון הראשון.
- שני עיתונים על אותו נושא בלי טענות נפרדות (unanswerable): שתי מחרוזות, עיתון אחד לכל אחת, כדי ש-Retrieve ימלא `source` פעמיים. בלי featured-in / CEO-filter כהופ נפרד.
- **Retry בפרודקשן:** אם יש `grade_note`, רק מחרוזות חדשות. הלוח הזה לא בודק retry, אבל הפרומפט חייב להישאר כשיר לפרודקשן.

הציון **לא** דורש מלאי זהה ל-`sub_questions`. הוא דורש שהקריאות ש-Retrieve בנה מהמחרוזות שלך יביאו את כל רשומות `facts`.

---

## מה לא שלך

| תחום | מי הבעלים | למה זה לא Gather |
|---|---|---|
| ארגומנטי `search_facts` (`question` מילה במילה, `source`, תאריכי ISO) | Retrieve (קפוא) | אתה שם עיתון/חלון **במחרוזת**. Retrieve מעתיק וממלא. |
| קטלוג מקורות / `run_resolve_source` | שירות השליפה | אחרי ש-Retrieve ממלא `source`. |
| `RETRIEVAL_TOP_K` / דירוג Chroma | שליפה | קפוא על 1. אל תעלה k. |
| Grade / Answer / `search_corpus` | קפוא | מחוץ ללוח. שורות `agent: unbound` ב-GT לא נספרות. |
| מלאי הופים מול `sub_questions` | לוח `live_gather_hops` (לא הציון) | ניסוח זהב אינו היעד. |
| באצ' Retrieve / שינוי `retrieve_agent.md` | אסור | ניסוי 8/11. הייצור מבודד. |

כישלון נשאר אצלך אם הפירוק מונע מ-Retrieve למלא או מההטמעה לפגוע: אריזת עיתונים, featured-in במקום טענה, עיתון על טענה לא נכונה, השמטת חלון פרסום, שתי טענות מאותו עיתון עם אותם שמות עצם, יכולות עם עיתון של מאמר אחר.

פספוס Top-1 **אחרי** שמחרוזת עומדת לבד, העיתון במחרוזת, ו-`source` מלא ב-`calls_*.csv` — זה דירוג. מותר לנסח מחדש את **סוג** הצורך כדי שההטמעה תפגע בקטע. אסור להדביק את משפט ה-`fact`. אסור לערוך אינדקס / GT / k / Retrieve.

---

## המשימה שלך (ה-pass היחיד)

**11/11** על קטעי הזהב של 11 שאלות ה-GT המקומי בבאצ' `search_facts` הראשון, עם **אפס leakage**, כש-Retrieve הקפוא רץ **הוף-הוף**.

עורך **רק** `project/src/prompts/gather_agent.md`.

**Pass:** שני קבצי `metrics_*.csv` החדשים ביותר ברצף מתוך `project/tests/live_gather_first_hop/outputs/`, אותו פרומפט Gather, `first_hop_success=1` בכל 11 השורות, `prompt_leak_hit=0`, מבנה ספק, `# Examples` סינטטי, בלי חיקויי מבחן, ו-`retrieve_agent.md` ללא שינוי.

`first_hop_success=1` אומר:

- `prompt_leak_hit=0`
- `runtime_error` ריק
- שאלה **answerable** (`unanswerable=0`): כל URL ב-`facts` נמצא ב-evidence **וכל** משפט `fact` תואם snippet ב-evidence (`first_hop_gold_complete=1`). זה **הקטעים**.
- שאלה **unanswerable** (Q04, Q09; `facts` ריק): אין קטעי זהב. עוברים כשיש מספיק קריאות עם `source` מלא לעיתונים שצוינו (`agent_source_call_count` ≥ `gt_source_required_count`).
- אם המשתמש נקב בחלונות פרסום (`gt_dated_required_count` > 0, Q08): הבאצ' ממלא פילטרי תאריך (`agent_dated_call_count` ≥ הספירה).
- בשאלות answerable עם עיתונים ב-GT: גם `agent_source_call_count` ≥ `gt_source_required_count` (בלי `source` הקטע הנכון בדרך כלל לא מגיע ב-Top-1).

הרץ **לא** משווה את ניסוח `sub_questions` ל-GT. הוא משווה evidence ל-`facts` ב-`project/src/data/ground_truth/Q01.json` … `Q11.json`.

---

## איזה קבצים להריץ (רק הלוח הזה)

תמיד מתיקיית `project/` הפנימית.

**זה ציון ה-11/11. תשתמש בו בכל פעם.** הוא מריץ Gather ואז Retrieve **מבודד** לכל מחרוזת — אותו חוזה כמו הייצור.

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_first_hop.run_live_gather_first_hop
```

צריך `.env` עם `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_MODEL`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`, ו-`vector_stores/facts_chroma`.

יש השהיה בין שאלות. כמה דקות עד רבע שעה. בלי הדפסה לקונסול. הצלחה = שלישיית CSV חדשה.

הריצות שולחות את 11 שאלות ההערכה ל-OpenRouter. זה צפוי. לשים אותן בפרומפט — לא.

### אל תריץ את אלה בתור הציון שלך

- `tests.live_gather_retrieve_once` — באצ' Retrieve. **8/11. מת.** לא הציון.
- `tests.live_gather_hops.run_live_gather_hops` — מלאי ניסוח מול `sub_questions`. **לא** הקטעים.
- `tests.live_gather_gt.run_live_gather_gt` — לולאה מלאה + Grade + עצירה
- `tests.live_retrieve_gt` — Retrieve על הופי GT מוכנים (כבר 11/11, קפוא; אל תשנה אותו)
- `tests.gt_facts_union_topk` — אורקל על תתי-שאלות GT עם k=5. אבחון בלבד
- e2e, oracle-Answer, לוחות Grade

---

## קבצי פלט — לאן הם יוצאים ואיך לקרוא אותם

כל ריצה כותבת שלישייה חדשה תחת `project/tests/live_gather_first_hop/outputs/`. כלום לא נדרס. פתח את החותמת **החדשה ביותר**.

| קובץ | מה זה | איך משתמשים |
|---|---|---|
| `metrics_YYYY-MM-DD_HH-MM-SS.csv` | לוח התוצאות. **זה N/11.** | סופרים שורות עם `first_hop_success=1`. |
| `hops_*.csv` | שורה אחת לכל **קטע זהב** (`facts`) | `url_in_evidence` / `snippet_in_evidence`. אין שורות ל-Q04/Q09. |
| `calls_*.csv` | שורה אחת לכל `search_facts` | רואים `question`, `source`, תאריכים, אריזה, featured-in. אם `source` ריק — Gather השמיט עיתון מהמחרוזת או ארז שניים. |

### עמודות `metrics_*.csv` שחשובות

- `first_hop_success` — 1 או 0. יעד 11.
- `first_hop_gold_complete` — כל URL+משפט זהב ב-evidence (1 אוטומטית ב-unanswerable).
- `url_recall` / `snippet_recall` — כמה מהקטעים הגיעו.
- `gold_url_count` — כמה URLs ייחודיים ב-`facts`.
- `facts_call_count` מול `required_facts_calls` — עודף קריאות (פירוק-יתר) או חוסר.
- `gt_source_required_count` מול `agent_source_call_count` — `source` ריק כי המחרוזת לא נתנה ל-Retrieve מה להעתיק.
- `gt_dated_required_count` מול `agent_dated_call_count` — חלון פרסום חסר מהמחרוזת (Q08).
- `missing_urls` / `missing_titles` — איזה קטע נפקד.
- `agent_queries` — המחרוזות ש-Retrieve **העתיק**, מחוברות ב-` | `.
- `prompt_leak_hit` — 1 מאפס **כל** הצלחה. סורק את `gather_agent.md` **וגם** `retrieve_agent.md`. אל תערוך את Retrieve; אם הוא «דלף» זה באג ישן, לא תיקון שלך.
- `runtime_error` — 429 / רשת / parse. לחכות, להריץ מחדש את **כל** 11.

### איך לקרוא פספוס (קודם בדוק אם Retrieve קיבל מחרוזת שהוא יכול למלא)

1. `calls_*.csv`: האם יש קריאה לכל צורך? האם `source` מלא כשהמשתמש שם עיתון **באותה מחרוזת**? האם Q08 מילא תאריכים כי החלון היה בטקסט?
2. `hops_*.csv`: `url_in_evidence=0` או `snippet_in_evidence=0` — הקטע הזה לא הגיע.
3. אם `source` מלא והמחרוזת עומדת לבד ועדיין `snippet_in_evidence=0` — Top-1 החזיר מאמר אחר. לנסח מחדש שמות עצם ייחודיים לצורך (בלי להדביק את משפט הזהב).
4. אם יש הופ featured-in / הופ-השוואה / הופ-שם ב-`agent_queries` — למחוק את **סוג** ההופ הזה מהפרומפט.
5. אם יכולת של מאמר אחד רצה עם `source` של עיתון אחר — לתקן שיוך עיתון במחרוזת, לא את Retrieve.

`missing_titles` / `gold_title` / משפט `fact` ב-GT מותר **לקרוא** כדי להבין איזה מאמר נפקד. **אסור** להדביק אותם בפרומפט.

429 → לחכות, להריץ שוב את כל 11. אל תערוך פרומפט בגלל תקלת רשת.

---

## מה נחשב קטע זהב (אל תדביק את המשפטים בפרומפט)

השדה `facts` בכל `Q0N.json`. לא `corpus`. לא `citations` (הם אותם משפטים ל-Answer). לא `search_corpus`.

| מזהה | קטעי `facts` | Unanswerable | מה החיפוש חייב להביא (כדי ש-Retrieve יצליח) |
|---|---|---|---|
| Q01 | 2 | לא | שני מאמרי Sporting News שונים; עיתון **בשתי** המחרוזות; שמות עצם שונים לכל משחק |
| Q02 | 2 | לא | TechCrunch במחרוזת אחת, The Verge בשנייה; בלי הופ-השוואה שלישי |
| Q03 | 3 | לא | שלושה צרכים, בלי עיתונים — Retrieve ישאיר `source` ריק, וזה נכון |
| Q04 | 0 | כן | שתי מחרוזות, עיתון אחד לכל אחת, כדי ש-`source` יתמלא פעמיים |
| Q05 | 3 | לא | שני צרכים בלי The Age, צורך אחרון עם The Age בלבד בתוך המחרוזת |
| Q06 | 2 | לא | The Age במחרוזת אחת, The Guardian בשנייה — העיתון חייב להופיע **במחרוזת** |
| Q07 | 3 | לא | שני מאמרי TechCrunch **שונים** (יכולת ראשונה מול debug/music) עם TechCrunch **בשתי** המחרוזות + מאמר Engadget (יום השנה) עם Engadget במחרוזת. **לא** לשים debug/music על Engadget |
| Q08 | 2 | לא | Independent Travel בשתי המחרוזות; חלון פרסום בטקסט לכל תאריך; Zermatt+Vail יחד, Tremblant לחוד |
| Q09 | 0 | כן | שתי קריאות עם `source` (שני העיתונים שצוינו, כל אחד במחרוזת שלו) |
| Q10 | 2 | לא | סכום השקעה בעיתון אחד במחרוזת; הקמה בעיתון השני במחרוזת. **אין** דרישת המילה `figure` בלוח הזה |
| Q11 | 2 | לא | שני צדדים, אותו עיתון **בשתי** המחרוזות, שני מאמרים, שמות עצם שונים |

אל תזכיר את הטבלה בפרומפט. אל תדביק URLs / כותרות / משפטי `fact`.

---

## בדיקת leakage (תעשה אותה בעצמך)

אחרי כל עריכה, חפש ב-`gather_agent.md` מול:

- `project/src/data/questions.json`
- `project/src/data/ground_truth/Q01.json` … `Q11.json`

שאלה מלאה, משפט `fact`, כותרת, URL, תת-שאלת זהב, או `arguments.question` מהקבצים האלה — דלפת. למחוק.

הרץ שם `prompt_leak_hit=1` על מחרוזות ≥24 תווים משני הפרומפטים. חיקויי מבחן **לא** נתפסים אוטומטית. זה עדיין עליך. אל «תנקה» דליפה ב-Retrieve — אל תיגע בו.

---

## מבנה הפרומפט לפי הספק (חובה לדבוק)

```markdown
# Identity
...

# Instructions
...

# Examples
```

`# Examples` **חובה**. בתוך הסעיף רק:

```text
<user_query>
...
</user_query>
<assistant_response>
...
</assistant_response>
```

קלט דוגמה: `{"question":"...","prior_queries":[],"grade_note":""}`. פלט: `{"sub_questions":[...]}`.

הדוגמאות חייבות להראות מחרוזות ש-Retrieve יכול לבלוע: עיתון **בתוך** הטענה כשיש עיתון; לא שני עיתונים במחרוזת; חלון פרסום בטקסט כשיש חלון; שמות עצם שונים לשני מאמרים מאותו עיתון.

אנגלית בלבד בקובץ. בלי קוד, env, סודות. קונטקסט לא נכתב בפרומפט.

להתחיל מ-`project/src/prompts/gather_agent.md` **הנוכחי** (10/11). אל תחזיר `tests/live_gather_gt/inputs/control.md` או `tests/live_gather_first_hop/inputs/control.md` (תבניות ישנות). אל תשחזר Marsh Courier / Oak mill / Vale Post.

אל תשחזר את כלל «כתוב `figure` ביחיד» רק כי לוח ההופים דרש אותו — הלוח הזה לא דורש את המילה. אם צד «בלי סכום» כבר שולף את קטע ההקמה, זה עובר.

---

## דוגמאות סינטטיות — חובה, תבנה אותן לבד

1. דומיין מזויף. Pebble Dispatch / Lichen Record / brine pump כבר בשימוש; אם נכשלו כחיקוי Q07 — החלף דומיין. אל תמחזר Oak mill / Harbor Gazette / Marsh Courier / Vale Post.
2. לפחות שני זוגות. עדיף ללמד **חוזה Retrieve**: שני צדדים עם עיתון בתוך כל מחרוזת; לא featured-in; שני מאמרים מאותו עיתון עם שמות עצם שונים; חלון פרסום בטקסט; יכולות נשארות עם העיתון הראשון ואירוע-לא-יכולת עם השני — בלי שלד של Q07 אחרי הסתרת שמות.
3. הסתר שמות עצם: אם זה עדיין Q01/Q04/Q07/Q08/Q10 — החלף את הזוג.
4. דוגמאות ל**הרגל שליפה ש-Retrieve יכול להעתיק**, לא לשכפול מלאי זהב.

---

## In / out

**עורך:**

- `project/src/prompts/gather_agent.md` **בלבד** כפרומפט
- צילומים `project/tests/live_gather_first_hop/inputs/candidate_<name>.md`

**מותר לקרוא (לא לערוך):**

- את התוכנית הזאת
- `project/tests/live_gather_first_hop/README.md` והרץ
- `project/src/agents/gather_agent.py`, `retrieve_agent.py` (איך נטען, מה נשלח) — בלי לשנות
- `project/src/prompts/retrieve_agent.md` — **קריאה בלבד, נעול**
- `project/src/data/questions.json`, `ground_truth/README.md`, `Q01.json`–`Q11.json` — להבין איזה קטע נפקד, לא להעתיק לפרומפט
- CSV חדשים תחת `project/tests/live_gather_first_hop/outputs/`

**אסור לערוך:**

- **`retrieve_agent.md` — בשום תירוץ**
- `grade_agent.md`, `answer_agent.md`
- JSON של GT, `questions.json`, `answers.json`
- agents, tools, services, repositories, orchestration, `conts.py`, `RETRIEVAL_TOP_K`
- `tests/live_gather_hops`, `tests/live_gather_gt`, `tests/live_retrieve_gt`, `tests/live_grade_gt`, `tests/live_gather_retrieve_once`
- אינדקסים
- כללי הניקוד של הרץ (אל «תתקן» זהב בהקלת הלוח)

אל תוסיף סוכנים. אל תקשור כלים ל-Gather. אל תשנה את Retrieve לפרוק מחרוזת ארוזה או לקבל רשימה בבת אחת. **השערה אחת בשם** לכל ריצה חיה.

---

## לולאה

1. **אין baseline מאפס.** הפרומפט שבפרודקשן הוא מועמד 10/11. ממשיכים ממנו. אל תריץ שוב «בלי עריכה» כצעד חובה אלא אם איבדת את המצב.
2. לצלם את Gather אל `project/tests/live_gather_first_hop/inputs/candidate_<short_hypothesis_name>.md`.
3. לערוך **רק** `gather_agent.md`. שינוי אחד בשם, שמכוון לחוזה Retrieve. `# Examples` סינטטי נשאר.
4. לבדוק friend-review, לחפש מול מחרוזות GT, ולוודא ש-`retrieve_agent.md` לא השתנה.
5. להריץ את פקודת הציון (`live_gather_first_hop` בלבד).
6. לפתוח את `metrics_*.csv` החדש ביותר. לספור `first_hop_success=1`. בפספוסים: `calls_*.csv` קודם (`source` / תאריכים), ואז `hops_*.csv`.
7. אם 11/11 — להריץ **שוב בלי עריכת פרומפט**. שני קבצים ברצף הם ה-pass.
8. אם לא — השערה חדשה אחת בשם שמתקנת איך המחרוזת נראית **ל-Retrieve**. לחזור.

אל «תתקן» זהב בעריכת GT. אל תמליץ על העלאת k, supervisor, סוכנים נוספים, או שינוי Retrieve בלי אישור מפורש חדש מהמשתמש.

אל תמליץ שוב על מודל Gather חזק יותר כמנוף ראשון. הסיבוב הוא `openai/gpt-4.1`. Retrieve נשאר `gpt-4o-mini` וקפוא.

---

## מצב נוכחי — 2026-08-28 (חובה לקרוא לפני עריכה)

### מה כבר סגור (לא לגעת)

- **Retrieve מבודד:** 11/11 פעמיים על הופי GT מוכנים. `retrieve_agent.md` קפוא. מעתיק `question` מילה במילה וממלא `source` / תאריכים **רק מהמחרוזת**.
- **Answer על evidence מושלם (oracle):** 11/11. מחוץ לסקופ.
- **באצ' Retrieve (קריאת LLM אחת על כל הרשימה):** נוסה ונכשל. `live_gather_retrieve_once` / `metrics_2026-08-28_22-30-09.csv` = **8/11**. רגרסיות: Q01 Top-1; Q06 בלי `source` על The Guardian; Q07 אותו פספוס. **לא לחזור.**

### למה עזבנו את לוח ההופים

`live_gather_hops` מנקד **מבנה מלאי** מול `sub_questions`. זה פרוקסי. הוא **לא** בודק אם Chroma החזיר את הקטע, וגם לא אם Retrieve מילא `source` מהמחרוזת.

אל תייעל למילת `figure` אלא אם הקטע עצמו נפקד.

### שיא לוח הקטעים (הבסיס שלך עכשיו)

פרומפט הפרודקשן הוא `candidate_abilities_first_outlet_example.md`. כמה מועמדים הגיעו ל-**10/11** על `live_gather_first_hop` עם `openai/gpt-4.1`. כולם נופלים על **Q07** בלבד.

| חותמת | מועמד | N/11 | Q07 |
|---|---|---|---|
| `21-43-32` | baseline hop-inventory (Marsh/Oak/Vale) | 8/11 | אריזה + clone לכל עיתון |
| `21-52-27` | `split_listed_claims` | 10/11 | generate→TC; debug/music→Engadget; anniversary→Engadget |
| `21-58-01` | `abilities_keep_first_outlet` | 10/11 | אריזת כל היכולות + clone |
| `22-04-21` | `split_abilities_second_outlet_event` | 10/11 | פיצול-יתר 8 קריאות, כפל לכל עיתון |
| `22-10-33` | `no_cross_product_pair_abilities` | 10/11 | זוג debug/music נכון, **עיתונים הפוכים** |
| `22-22-14` | `abilities_first_outlet_example` **(פרודקשן)** | 10/11 | generate→TC; debug/music→Engadget; anniversary→Engadget |
| `22-30-09` | אותו Gather + באצ' Retrieve | 8/11 | אל תחזור |

עוברים ב-10/11: Q01–Q06, Q08–Q11.  
Q07 נשאר: קטע TechCrunch «One year later…» (debug code / compose music) נפקד, כי Gather שם את הזוג על **Engadget**. Retrieve מעתיק `source=Engadget` ולא יכול לתקן. שיוך נכון ש-Retrieve יצליח איתו: יכולת ראשונה + TechCrunch; debug+music + TechCrunch (שמות עצם שונים מהראשונה); יום השנה + Engadget בלבד.

Q01 ב-10/11 עובד עם מחרוזות «What did the Sporting News report about…» ועם yes-no; לפעמים Top-1 מפיל אותו בלי שינוי פירוק (ראה באצ' 8/11). אל תשבור את השיוך Sporting News בשתי המחרוזות.

### מה לנסות עכשיו (השערה אחת בשם)

המטרה: כל מחרוזת היא הודעת Retrieve ש-Top-1 שלה הוא קטע הזהב של הצורך הזה.

- **Q07:** שתי מחרוזות יכולת עם **העיתון הראשון בלבד**; מחרוזת אירוע-לא-יכולת עם **העיתון השני בלבד**. לא להחליף. לא לשכפל. לא featured-in.
- לפצל שני מאמרים מאותו עיתון עם שמות עצם **שונים**
- לשים עיתון בתוך הטענה, לא כהופ featured-in — כדי ש-Retrieve ימלא `source`
- לא לארוז שני עיתונים
- לא להוסיף הופ-השוואה אחרי שני צדדים
- Q08: שני חלונות פרסום בטקסט, שני מקומות באותו תאריך נשארים יחד
- Q04/Q09: שתי מחרוזות, עיתון אחד לכל אחת
- Q06: The Guardian / The Age חייבים להופיע **במחרוזת**, לא רק בשאלת האב

**אין כלל עצירה.** רצים עד 11/11 פעמיים בלי leakage. כל מועמד חייב `# Examples` סינטטי.

אחרי רגרסיה: להחזיר הוראות שעבדו על **הלוח הזה** (10/11), לתקן רק את שיוך העיתון של יכולות מול אירוע, להריץ שוב. לא לגעת ב-Retrieve.

---

## אין כלל עצירה

לא עוצרים עד שני קבצי `metrics_*.csv` ברצף עם `first_hop_success=1` בכל 11 השורות, `prompt_leak_hit=0`, `# Examples` סינטטי, ו-Retrieve ללא שינוי. אין תקרת ריצות. חיקוי מבחן = למחוק את הזוג, לכתוב דוגמה אחרת, להמשיך.

אל תערוך Retrieve, Grade, Answer, k, או את הגרף. דוח ביניים מותר כשיש 11/11 פעמיים, או כשהמשתמש מבקש סטטוס. בסטטוס: נתיבי CSV, N/11 לכל מועמד, מזהים שנשארו עם `url_recall`/`snippet_recall` ו-`source` ריק או לא, `candidate_*.md` הטוב ביותר — ואז ממשיכים.

---

## הודעה ראשונה לצ'אט הבא (להדביק את זה)

קרא את `project/plans/gate4-gather-gold-chunks-prompt-goal.md` מהכותרת הראשונה עד הסוף, כולל «מצב נוכחי — 2026-08-28». עבור על בדיקות friend-review.

אתה ממשיך עבודה, לא מתחיל מאפס. הציון הוא קטעי `facts` בבאצ' `search_facts` הראשון, לא מלאי הופים. Gather חייב להתאים ל-**Retrieve הקפוא**: הוף מבודד, מעתיק את המחרוזת מילה במילה, ממלא `source`/תאריכים רק ממנה. **אסור לגעת ב-`retrieve_agent.md`.** הפרומפט היחיד שמותר לערוך: `gather_agent.md`.

הפרודקשן הוא 10/11 (`metrics_2026-08-28_22-22-14.csv`). נשאר Q07: debug/music רצו עם Engadget במקום TechCrunch. באצ' Retrieve נכשל 8/11 — לא לחזור עליו.

מנקד **רק** עם:

```text
cd project
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_first_hop.run_live_gather_first_hop
```

מודל Gather: `openai/gpt-4.1`. **אין כלל עצירה.** רץ עד 11/11 `first_hop_success` פעמיים. בלי data leakage ובלי חיקויי מבחן.
