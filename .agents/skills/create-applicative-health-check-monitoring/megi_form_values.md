# Megi Form Values — Copy-Paste Ready

> Submit one Megi request per microservice. Below are the exact field values for each.

---

## 🟦 Request — `<microservice_slug>`

| Field | Value |
|---|---|
| **Event message (in English)** | `<ALERT_NAME>` |
| **שם יישום** | `prod :: <PROJECT_DISPLAY_NAME>` |
| **האם ניטור ברמת שרת?** | `לא` |
| **גורם מטפל בתקלה** | `<TEAM_NAME>` |
| **שעות מענה טלפוני** | `Day Only` |
| **האם לשלוח התראות לNOC?** | `כן` |
| **קובץ מצורף** | [`<microservice_slug>_alerts.xlsx`](<microservice_slug>_alerts.xlsx) |

### פירוט (מהות הניטור)
```
Two health check endpoints for the <microservice_slug> microservice.
1) /applicative-health-check verifies live connectivity to: <comma-separated dependency labels>.
2) /redis-queues-check verifies the Redis queue(s) <REDIS_QUEUE_CONST_NAMES> and reports their current depth.
The applicative endpoint returns is_ok=true/false per dependency; the Redis queue endpoint returns queue depth only. Used to detect production outages and trigger NOC alerts.
```

### פירוט (חובה — NOC)
```
Endpoints:
  GET <PRODUCTION_URL_BASE>/api/monitor/applicative-health-check
  GET <PRODUCTION_URL_BASE>/api/monitor/redis-queues-check
  Method: GET
  Auth: none (internal cluster)
  Max execution time: 60 seconds
  Recommended polling frequency: every 10 minutes

Response (HTTP 200) — applicative-health-check:
  list of objects, each with:
    - service_name: str  (e.g., <example dependency labels>)
    - is_ok: bool
    - description: list[str] | null   (error details when is_ok=false)

Response (HTTP 200) — redis-queues-check:
  list of objects, each with:
    - service_name: str  (e.g., "Redis Queue (<REDIS_QUEUE_CONST_NAME>)")
    - queue_depth: int | null   (current pending items; null when the Redis probe failed)

Alert condition:
  Trigger when ANY element of /applicative-health-check has is_ok=false (the Redis dependency is included there).
  /redis-queues-check exposes queue depth only and is not used for alerting.

Severity: Critical (SMS + email)

Action for NOC on alert:
  1. Verify the failure by calling both endpoints; look for any element with "is_ok": false.
  2. Restart the pod in OpenShift:
        Project: <OPENSHIFT_PROJECT>
        App:     <OPENSHIFT_APP>
  3. Re-run both endpoints after the pod is Ready (~30 sec).
  4. If still failing after 2 restart cycles, escalate to:
        <CONTACT_NAME> — <CONTACT_EMAIL> — <CONTACT_PHONE>
```

---

## 📧 מייל ל-NOC (`<NOC_CONTACT_EMAIL>`)

> **נושא (Subject):** `ניטור פרויקט <PROJECT_DISPLAY_NAME> — פרטי נמען להתראות`

```
שלום,

אנו מקימים ניטור אפליקטיבי דרך Megi עבור פרויקט "<PROJECT_DISPLAY_NAME>" של מחלקת <TEAM_NAME>, הכולל <N> מיקרו-סרביסים בפרודקשן.

נמען ההתראות (Critical = SMS + מייל; Major/Minor = מייל בלבד):
   שם:      <CONTACT_NAME>
   מייל:    <CONTACT_EMAIL>
   טלפון:   <CONTACT_PHONE>

שם קבוצת הנמענים:
   <NOTIFICATION_GROUP>

בקשות הניטור שהוגשו ב-Megi:
   1. <ALERT_NAME>    — ניטור <microservice_slug>

כל אלרט נשלח ברמת חומרה Critical ובתדירות הרצה של פעם ב-10 דקות.

תודה,
<CONTACT_NAME>
מחלקת <TEAM_NAME>
```

> 💡 **טיפ:** מומלץ לשלוח מייל זה **אחרי** הגשת הבקשות ב-Megi, כדי שניתן יהיה לקשר את קבוצת הנמענים `<NOTIFICATION_GROUP>` ישירות לאלרטים שכבר רשומים במערכת.

---

## 📧 Email to NOC — English version (backup)

> **Subject:** `<PROJECT_DISPLAY_NAME> monitoring — alert recipient`

```
Hi,

We are setting up application-level monitoring for the <PROJECT_DISPLAY_NAME> project (<N> microservices in production) via Megi.

Alert recipient (Critical = SMS + email; Major/Minor = email only):
  - <CONTACT_NAME>  —  <CONTACT_EMAIL>  —  <CONTACT_PHONE>

Notification group name:
  <NOTIFICATION_GROUP>

Megi requests submitted:
  1. <ALERT_NAME>    — monitoring <microservice_slug>

All alerts are Critical severity and run every 10 minutes.

Thanks,
<CONTACT_NAME> — <TEAM_NAME>
```
