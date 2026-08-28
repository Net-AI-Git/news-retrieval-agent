# GOAL — Retrieve isolated hop, 11/11 מול GT, בלי leakage

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-28  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/retrieve_agent.md`

הקובץ הזה הוא **המפרט היחיד** של הצ'אט הזה. אל תקרא תוכניות אחרות בשביל ניסוח הפרומפט. אל תעתיק תבניות פרומפט ישנות. אל תשתמש ב-`tests/live_gather_first_hop` או ב-`tests/live_gather_gt` כציון.

---

## Friend review — תיכשל אם תעשה את אלה

1. **Leakage זה רמאות.** אסור לשים בתוך `retrieve_agent.md` שאלות ממערך ההערכה, תשובות, כותרות מאמרים, קטעי עובדות, כתובות URL, תת-שאלות, מחרוזות `question` של כלי מה-GT, או “אותה שאלה עם שמות מזויפים”. אם חומר הלימוד מכיל את המבחן, הציון לא תקף גם ב-11/11.
2. **אין דוגמאות מהמבחן שלנו.** `# Examples` הוא אופציונלי ובדרך כלל טעות. אם אתה מוסיף דוגמאות — תמציא אותן בעצמך, בתחום בדוי. אם מישהו שראה את 11 שאלות המבחן יזהה את הדוגמה אחרי שמסתירים שמות פרטיים — תמחק אותה.
3. **קצר.** `retrieve_agent.md` בפרודקשן חייב להישאר **מתחת ל-40 שורות** ו-**מתחת ל-350 מילים**. לקצר, לא להוסיף בלי למחוק.
4. **מבנה ספק בלבד.** המודל הוא `openai/gpt-4o-mini`. **חובה** להשתמש במתווה הזה ורק בו:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (אופציונלי; עדיף בלי)
   - **אסור** לשים `# Context` בקובץ. התת-שאלה המבודדת נשלחת כהודעת user.
5. **אסור תבנית ישנה.** אל תשאיר ואל תתרגם `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, או `RESPONSE FORMAT`. אל תשתמש בתגי XML של Claude כמתווה ראשי (`<role>`, `<decision_policy>`).
6. **אל תלמד דירוג או שם קנוני של עיתון.** שמות בקטלוג ו-top-k הם לא הסוכן הזה. ללמד “תמיד תוציא Sporting News בדיוק” או להדביק עובדות זהב זה leakage וגם מחוץ לתחום.

אחרי כל עריכה, לפני הרצה: פתח את `retrieve_agent.md` וודא שששת הבדיקות האלה עוברות.

---

## מה המוצר הזה (אין לך קונטקסט קודם)

הריפו הזה עונה על שאלות מתוך עובדות חדשות באינדקס מקומי. לולאת התשובה מפוצלת לסוכנים:

- **Gather** — מפרק את שאלת המשתמש המלאה לתת-שאלות עצמאיות. **לא שלך.**
- **Retrieve** — **זה שלך.** רואה **תת-שאלה אחת**. ממלא **קריאה אחת** ל-`search_facts`.
- **Tools / Chroma / דירוג** — רצים אחרי Retrieve. **לא שלך.**
- **Grade / Answer** — אחר כך. **לא שלך.**

ארגומנטים של `search_facts`:

- `question` (חובה) — מחרוזת החיפוש
- `source` (אופציונלי) — שם עיתון, רק כשהתת-שאלה הזו ממנה עיתון
- `published_from` / `published_to` (אופציונלי) — חלון תאריך **פרסום** ב-ISO-8601

קוד הריצה של Retrieve כבר קיים. אתה משנה רק את קובץ הפרומפט.

```text
project/src/agents/retrieve_agent.py
```

מה הקובץ הזה כבר עושה (אל תערוך אותו):

- טוען את `project/src/prompts/retrieve_agent.md` כהודעת system
- שולח `HumanMessage(task_data["sub_question"])` — **רק** את המחרוזת הזו
- קושר את הכלי `search_facts` עם `tool_choice="search_facts"` (קריאה אחת בדיוק)
- משתמש ב-`OPENAI_MODEL` (`openai/gpt-4o-mini`), `temperature=0`, `seed=151`

כי הודעת המשתמש היא רק התת-שאלה המבודדת, עיתון שמופיע בהופ אח **לא יכול** להופיע בהופ הזה — אלא אם **אתה** שמת אותו בפרומפט. לכן leakage בפרומפט שובר גם בידוד.

---

## המשימה שלך

להגיע ל-**11/11** בלוח Retrieve-only, פעמיים ברצף, עם **אפס data leakage**.

יש 11 שאלות GT מקומיות (`Q01` … `Q11`) תחת `project/src/data/ground_truth/`, לפי הסכימה ב-`project/src/data/ground_truth/README.md`. הלוח **לא** שולח את שאלת האב. לכל שאלה הוא לוקח רק שורות `expected_tool_calls` שבהן `agent` הוא `"retrieve"`. הקלט ל-Retrieve הוא התת-שאלה המבודדת מ-`sub_questions` לפי `sub_question_index` (אם חסרה — `arguments.question`). שורות `agent: "unbound"` (`search_corpus` ב-Q04/Q09) לא נכנסות ללוח הזה.

**עמידה ביעד:** שני קבצי `metrics_*.csv` החדשים ביותר ברצף, אותו פרומפט Retrieve, `retrieve_success=1` בכל 11 השורות, `prompt_leak_hit=0`, מבנה ספק, מגבלות אורך, בלי טקסט מבחן ובלי חיקויים.

`retrieve_success=1` על שאלה אומר ש**כל** ההופים המבודדים של השאלה עברו:

- קריאת כלי אחת בדיוק, שם `search_facts`
- `question` הוא העתק מילולי של מחרוזת הקלט (אחרי נירמול רווחים). שומר פעלים ושמות של המשתמש. לא לשכתב, לא לסכם, לא “לשפר”
- אם להופ ב-GT יש `source`: ה-`source` של הסוכן לא ריק, מועתק **מהמחרוזת הזו** (טוקן קצר; שגיאות כתיב מותרות), ותואם את העיתון — לא אדם / חברה / מוצר / נושא מתוך אותה מחרוזת
- אם להופ ב-GT אין `source`: הסוכן משמיט `source` (ריק)
- אם להופ ב-GT יש `published_from` / `published_to`: הסוכן ממלא את שניהם, ISO-8601 עם offset UTC מפורש, אותו יום קלנדרי כמו ב-GT. הצורה הרצויה: התחלה `T00:00:00+00:00`, סוף `T23:59:59+00:00`. חצות בלי offset נכשל
- אם להופ ב-GT אין חלון פרסום: הסוכן משמיט את שני שדות התאריך. תאריכי אירוע נשארים בתוך `question`
- המודל לא עונה למשתמש (אין טקסט assistant לא-ריק)
- סריקת הדלפה של הפרומפט היא 0

**לא נמדד (אל תרדוף אחרי זה):**

- URL / משפט זהב / מקום 1 ב-Chroma
- שם קנוני בקטלוג (השם המלא של העיתון מול טוקן קצר מהמחרוזת). הקנוניזציה היא `run_resolve_source` בקוד: exact → substring ייחודי → embedding; אם לא נפתר — בלי פילטר מקור ב-Chroma
- Top-k / דירוג. Q01 עם `source` מלא מעיתון במחרוזת והגולד לא rank 1 היא בעיית retrieval, לא כשל פרומפט Retrieve בלוח הזה
- אריזה של Gather (שני עיתונים במחרוזת אחת). הלוח הזה כבר מזין הופים מפוצלים מה-GT. אל תערוך את Gather כדי “לעזור” ל-Retrieve

---

## מה ללמד בפרומפט (הרגלים כלליים, לא שורות מבחן)

מלמד הרגלים. לא מלמד את 11 השאלות.

- תת-שאלה מבודדת אחת נכנסת, `search_facts` אחד יוצא. אף פעם לא עונה.
- מעתיק את מחרוזת הקלט ל-`question`. לא מוסיף את שאלת האב. לא מוסיף הופים אחים. לא מקנן ישויות בתוך `question`.
- **עיתון** שמופיע במחרוזת **הזו** → `source` = טוקן קצר מתוך המחרוזת הזו. שגיאות כתיב מותרות. אם במחרוזת הזו אין עיתון → משמיט `source`.
- אסור לשים אדם, חברה, מוצר, נושא, או מציין כללי כמו “news outlet” ב-`source`. שם חברה או בורסה בטקסט הוא לא עיתון.
- **חלון פרסום** שמופיע במחרוזת הזו (מתי המאמר פורסם) → `published_from` / `published_to` שמכסים את היום הקלנדרי ב-ISO-8601 עם offset UTC. תאריכים שהם חלק מהאירוע נשארים רק ב-`question`.
- לא ממציא עיתון שלא נמצא במחרוזת הזו. לא מעתיק עיתון מדוגמה בפרומפט אל הופ שלא ציין עיתון.

---

## מבנה הפרומפט לפי הספק (חובה לדבוק בזה)

קובץ: `project/src/prompts/retrieve_agent.md`  
שפה: אנגלית בלבד.  
בלי Python, YAML, JSON, Jinja, קריאות env, או סודות בקובץ הפרומפט.

המתווה המדויק:

```markdown
# Identity
...

# Instructions
...

# Examples
<user_query>
...
</user_query>
<assistant_response>
...
</assistant_response>
```

`# Examples` אופציונלי. עדיף בלי. אם כוללים אותו — בדיוק שני התגים האלה. קונטקסט לא נכתב לקובץ; הריצה שולחת את התת-שאלה כהודעת user.

מתחילים מקובץ הפרודקשן הנוכחי. לא משחזרים את `tests/live_gather_gt/inputs/control.md` ולא שום פרומפט Gather.

---

## אם רוצים דוגמאות — לחפש ולבנות אותן לבד

המסמך הזה לא נותן גופי דוגמה. אל תעתיק הופים מה-GT. אל תשכפל את 11 השאלות עם שמות מוחלפים.

הדרך המותרת:

1. לקרוא את `project/src/prompts/AGENTS.md` רק בשביל תגי הדוגמה של הספק.
2. להמציא תחום בדוי (עיירה בדויה, עיתון בדוי, כתובות `https://….example/…` מזויפות).
3. להשתמש בדוגמאות רק ל**פורמט**: העתקה מילולית של מחרוזת המשתמש ל-`question`; השמטת `source` כשאין עיתון; טוקן עיתון קצר כשהמחרוזת הבדויה ממנה עיתון; פילטר תאריכים רק לחלון פרסום בדוי.
4. למחוק את הדוגמה אם אחרי הסתרת שמות פרטיים היא עדיין נראית כמו המבחן שלנו (אותו מלכוד: שני עיתונים ואסור שאחד יזלוג להופ השני, שם חברה שנטעה לעיתון, יום פרסום מול תאריך אירוע).

עדיף zero-shot. בלוק דוגמאות ארוך בדרך כלל נכשל במגבלת האורך וגם בסיכון הדלפה.

---

## בפנים / בחוץ

**מותר לערוך:**

- `project/src/prompts/retrieve_agent.md` (קובץ הפרודקשן היחיד שמשנים)
- צילומי מצב `project/tests/live_retrieve_gt/inputs/candidate_<name>.md`
- שורת Status ב-`project/tests/live_retrieve_gt/README.md` אחרי הרצה, אם רוצים

**אסור לערוך:**

- `gather_agent.md`, `grade_agent.md`, `answer_agent.md`, כל פרומפט אחר
- `retrieve_agent.py`, סוכני Gather / Grade / Answer, כלים, שירותים, repositories, orchestration, `conts.py`, schemas
- JSON של GT, `questions.json`, `answers.json`, `facts.json`
- `tests/live_gather_first_hop`, `tests/live_gather_gt`, `tests/live_grade_gt`, `tests/live_search_facts_gt_calls`
- vector stores, top-k, קטלוג מקורות, `run_resolve_source`

לא להוסיף סוכנים. לא לקשור `search_corpus`. לא להריץ e2e, oracle-Answer, לוחות Grade, או לוח Gather first-hop כציון.

השערת ניסוי **אחת בשם** לכל הרצה חיה.

---

## הלוח (זה ה-11/11)

תמיד מתוך תיקיית `project/` הפנימית. ב-PowerShell:

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_retrieve_gt.run_live_retrieve_gt
```

צריך `project/.env`:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL` (`openai/gpt-4o-mini`)

**לא** צריך את חנות Chroma ולא את `OPENAI_EMBEDDING_MODEL`. הלוח רק מבקש ממודל הצ'אט למלא את קריאת הכלי. הוא לא מריץ את `search_facts`.

ההרצות האלה שולחות payload של הערכה ל-OpenRouter. זה צפוי. מספר ההופים הוא מספר שורות `agent: "retrieve"` ב-GT הנוכחי (הפסקה 12 שניות בין הופים). בלי `print` לקונסול; הצלחה היא זוג CSV חדש.

אל תשתמש ב:

```text
uv run python -m tests.live_gather_first_hop.run_live_gather_first_hop
uv run python -m tests.live_gather_gt.run_live_gather_gt
```

הלוחות האלה מערבבים Gather + פגיעות retrieval. הם ייענשו אותך על אריזה של Gather ועל פספוסי rank-1 שזה לא חוזה Retrieve.

פירוט נוסף: `project/tests/live_retrieve_gt/README.md`.

---

## קבצי פלט — לאן הם יוצאים ואיך בודקים אותם

נכתבים אל:

```text
project/tests/live_retrieve_gt/outputs/
```

שני קבצים לכל ריצה, אותו חותמת זמן:

- `metrics_YYYY-MM-DD_HH-MM-SS.csv` — **שורה אחת לכל שאלה** (11 שורות). זה ציון ה-11/11
- `hops_YYYY-MM-DD_HH-MM-SS.csv` — **שורה אחת לכל הופ Retrieve ב-GT** (`agent: "retrieve"`). זה קובץ הדיבאג

UTF-8 עם BOM (`utf-8-sig`) כדי שאקסל ייפתח אותם. החותמת החדשה ביותר = הריצה הזו. CSV חלקי אחרי קריסה אינו ציון; להריץ מחדש את כל החבילה.

### `metrics_*.csv` — איך סופרים 11/11

פתח את קובץ ה-metrics החדש ביותר. ספור שורות שבהן `retrieve_success` הוא `1`. המספר הזה מתוך 11 הוא הציון.

| עמודה | מה זה אומר |
| --- | --- |
| `question_id` | `Q01` … `Q11` |
| `hop_count` | כמה שורות `agent: "retrieve"` יש ל-GT בשאלה |
| `hops_passed` | כמה מהם עברו. חייב להיות שווה ל-`hop_count` |
| `retrieve_success` | `1` רק אם כל ההופים עברו **וגם** `prompt_leak_hit=0` |
| `prompt_leak_hit` | `1` אם `retrieve_agent.md` מכיל מחט מבחן. אז **כל** השאלות נכשלות |
| `rewritten_question_count` | הופים שלא העתיקו את מחרוזת הקלט ל-`question` |
| `source_fail_count` | הופים עם `source` חסר / עודף / לא נכון |
| `dates_fail_count` | הופים עם פילטר תאריכים חסר / עודף / לא נכון |
| `call_fail_count` | הופים שלא הוציאו בדיוק `search_facts` אחד |
| `answered_count` | הופים שגם כתבו טקסט למשתמש |
| `fail_reasons` | קודי כשל ייחודיים בשאלה |
| `runtime_error` | טקסט חריגה אם קריאת המודל קרסה |

### `hops_*.csv` — איך מדביגים פספוס

סנן ל-`hop_success=0`. קרא `fail_reason`, ואז השווה `sub_question` (מה ש-Retrieve ראה) מול `agent_question` / `agent_source` / `agent_published_*`.

| `fail_reason` | מה השתבש | מה ללמד (כללי) |
| --- | --- | --- |
| `prompt_leak` | טקסט מבחן נמצא בפרומפט | למחוק. הריצה לא תקפה עד שהדלפה 0 |
| `rewritten_question` | `question` אינו העתק של הקלט | ללמד העתקה מילולית; לשמור פעלים ושמות |
| `source` | עיתון חסר, `source` עודף כשאין עיתון, טוקן לא מהמחרוזת הזו, או טוקן שאינו העיתון שצוין | ללמד: עיתון במחרוזת **הזו** → טוקן קצר מהמחרוזת **הזו**; אחרת להשמיט; אף פעם לא אדם/חברה/נושא |
| `dates` | חלון פרסום חסר, תאריכים עודפים בהופ של אירוע בלבד, בלי offset UTC, או יום קלנדרי לא נכון | ללמד ISO-8601 עם offset; תאריכי אירוע נשארים ב-`question` |
| `call_count` / `wrong_tool` | לא בדיוק `search_facts` אחד | ללמד קריאה אחת, לא לענות. הריצה כבר כופה את הכלי; לא להילחם בזה |
| `answered` | טקסט assistant לא ריק | ללמד אף פעם לא לענות |
| `runtime_error` | קריסת API / ייבוא | אם 429 — לחכות ולהריץ מחדש את **כל** החבילה. קובץ חלקי אינו ציון |

לדבג CSV מותר. להדביק את השורה לפרומפט אסור.

### בדיקת הדלפה (לעשות גם לבד)

אחרי כל עריכה, לחפש ב-`retrieve_agent.md` מול `project/src/data/questions.json` ו-`project/src/data/ground_truth/*.json` (הקבצים החיים, לא עותק ישן). כל שאלת מבחן מלאה, משפט עובדה, כותרת, URL, תת-שאלה, או מחרוזת `question` צפויה מהקבצים האלה היא הדלפה. למחוק.

הרץ מסמן `prompt_leak_hit=1` על המחטים האלה (אורך ≥ 24, מדלג על תשובות קצרות כמו Yes/No) ומאפס כל `retrieve_success`. חיקויים נשארים עליך.

מותר לפתוח קבצי GT כדי להבין פספוס. אסור להעתיק את הניסוח שלהם לפרומפט.

---

## הלולאה

1. לצלם את פרומפט הפרודקשן הנוכחי אל `project/tests/live_retrieve_gt/inputs/candidate_<name>.md` (ו להשאיר את `inputs/control.md` כקובץ ההתחלה).
2. לערוך רק את `project/src/prompts/retrieve_agent.md`. לשמור קצר. שינוי אחד בשם לכל ריצה.
3. לבדוק שוב Friend review וחיפוש מחרוזות GT.
4. להריץ את לוח Retrieve. לקרוא את `metrics_*.csv` החדש ביותר. בפספוסים — לקרוא `hops_*.csv`.
5. אם 11/11 — להריץ שוב **בלי** עריכת פרומפט. שני קבצי 11/11 ברצף הם העמידה ביעד.
6. אם לא — השערת ניסוי חדשה אחת בשם. לחזור.

לא “לתקן” זהב בעריכת GT. לא להעלות `k`. לא לקנן שמות עיתונים בפרומפט.

אם המילוי נכון בבירור ברוב המזהים וכמה עדיין נופלים רק בגלל שונות מודל (אותו פרומפט, הופים מתהפכים) — **לעצור ולדווח**. לא להמשיך לדחוס את הפרומפט.

---

## מתי לעצור (לדווח, לא להרחיב תחום)

לעצור עבודת פרומפט אם **אחד** מאלה נכון. לא לערוך Gather, Grade, Answer, כלים, או k.

1. **6 הרצות כנות** של לוח Retrieve (candidate שמור + `metrics_*.csv` מלא + בלי הדלפה) ועדיין אין שני 11/11 נקיים.
2. **אותו סוג כשל** על אותם מזהי הופ אחרי שתי הרצות ייעודיות בלי שיפור: שאלה משכתבת, `source` חסר, `source` עודף, תאריכים חסרים, תאריכים עודפים.
3. **תיקון סוג אחד שובר סוג אחר** (למשל למלא `source` בכל הופ, או להשמיט אותו בהופים שממנים עיתון).
4. הרעיון הבא היחיד הוא חיקוי מבחן.
5. שלוש הרצות כנות בטווח של נקודה אחת עם אותם מזהים שמתהפכים.

בדיווח: נתיבי CSV, N/11 לכל candidate, מזהי שאלות שנשארו ו-`fail_reason`, האם `source` / תאריכים היו ריקים או עודפים, ה-`candidate_*.md` הנקי הטוב ביותר. לא להמליץ על Grade, עריכות Gather, מפקח, סוכנים נוספים, או שינוי `RETRIEVAL_TOP_K`.

---

## החלטות ארכיטקטורה (סגורות — לכבד אותן)

- Retrieve הוא סוכן נפרד מ-Gather. הקלט הוא `HumanMessage(sub_question)` מבודד אחד. בלי שאלת אב, בלי אחים.
- הופי Retrieve ב-GT הם שורות `expected_tool_calls` עם `agent: "retrieve"`. שורות `unbound` אינן חלק מהמשימה.
- `tool_choice="search_facts"` הוא קוד פרודקשן. הפרומפט לא מנסה לקרוא לכלים אחרים ולא לדלג על הקריאה.
- קנוניזציית קטלוג נשארת ב-`run_resolve_source`, לא בפרומפט.
- דירוג נשאר ב-retrieval. הלוח הזה לא מריץ Chroma.
- פרומפט הפרודקשן חי ב-`prompts/retrieve_agent.md`; שם הקובץ תואם ל-`retrieve_agent.py`.

---

## התוצר הסופי

`retrieve_agent.md` קצר במבנה הספק, שקולע **11/11 `retrieve_success` פעמיים** על `tests/live_retrieve_gt` עם `prompt_leak_hit=0`, ועם צילומי מצב תחת `tests/live_retrieve_gt/inputs/`. בלי שינוי קבצי פרודקשן אחרים.

---

## Open questions

- none

---

## הודעת הפתיחה לצ'אט הזה

קרא את `project/plans/gate4-retrieve-isolated-hop-prompt-goal.md` מהכותרת הראשונה עד הסוף. עבור על בדיקות Friend review. אתה בעלים רק של `project/src/prompts/retrieve_agent.md`. מודדים רק עם `tests/live_retrieve_gt` (הופים מ-`expected_tool_calls` עם `agent: "retrieve"` ב-`src/data/ground_truth`, מילוי כלי מול GT, בלי Gather, בלי Chroma, בלי שורות `unbound`). הצלחה היא 11/11 `retrieve_success` פעמיים, בלי טקסט הערכה ובלי חיקויים. `question` של הכלי חייב להיות העתק מילולי של קלט התת-שאלה המבודדת. `source` רק כשהמחרוזת הזו ממנה עיתון. חלונות פרסום מקבלים פילטרי ISO-8601 עם offset UTC; תאריכי אירוע נשארים ב-`question`. שמות קנוניים ו-rank-1 הם לא התפקיד שלך. אם אתה רוצה דוגמאות — תמציא אותן לבד. עצור לפי הסעיף “מתי לעצור”.
