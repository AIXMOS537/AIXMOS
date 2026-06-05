# TMMT — Airtable is the Source of Truth
## Effective immediately. No exceptions.

---

## THE RULE
If it is not in Airtable, it does not exist.
No text message, no WhatsApp note, no memory counts.
Airtable only.

---

## WHAT GETS UPDATED AND WHEN

### LEADS (Incoming Leads table)
| Event | Update Airtable |
|-------|----------------|
| New lead comes in | Immediately — name, phone, source |
| You call or text them | Same day — what happened, your initials, date |
| They fill the form | Same day — "Form filled [DATE]" |
| No response after 3 days | Update notes — "3 days no response [DATE]" |
| Not interested | Update notes — "Not interested [DATE]" + mark closed |
| They become a customer | Update status — "Current Customer" |

### FLEET (Fleet table)
| Event | Update Airtable |
|-------|----------------|
| New car added | Immediately — name, year, plate, partner, price, status |
| Car rented out | Same day — status → Rented |
| Car returned | Same day — status → Available |
| Car goes to shop | Same day — status → Under Maintenance |
| Car retired | Same day — status → Retired |
| Price changes | Same day — update weekly price |
| Partner changes | Same day — update partner name |

### CUSTOMERS (Active Customers table)
| Event | Update Airtable |
|-------|----------------|
| Customer signs up | Same day — full name, phone, vehicle, start date, payment amount |
| Payment received | Same day — update Last Payment Date |
| Payment missed | Same day — note it with date and amount |
| Vehicle swapped | Same day — update vehicle assigned |
| Customer removed | Same day — update status to Removed |
| Service done | Same day — add service note with date |

### PAYMENTS (Customer Payments table)
| Event | Update Airtable |
|-------|----------------|
| Payment received | Same day — amount, date, method |
| Payment missed | Same day — update Past Due amount |
| Payment plan agreed | Same day — note the agreement |
| Vehicle repossessed | Same day — status + total balance owed |

### TICKETS & TOLLS (Tickets table)
| Event | Update Airtable |
|-------|----------------|
| Ticket received | Same day — citation #, type, amount, vehicle, date |
| Customer notified | Same day — note in description |
| Customer pays | Same day — update balance status |
| Ticket disputed | Same day — note dispute status |

---

## FORMAT FOR NOTES
Always write notes like this:
```
[DATE] -- [YOUR INITIALS] -- [WHAT HAPPENED]
```
Example:
```
5/18/26 -- RK -- Called, no answer. Texted follow-up.
5/19/26 -- WA -- Replied, sending form today.
5/20/26 -- RK -- Form filled. Moving to onboarding.
```

---

## WHAT HAPPENS IF YOU DON'T UPDATE
1. The morning report flags your record as incomplete
2. Taha sees it every morning
3. You get asked about it in the group chat
4. Repeat offenses = performance issue

---

## THE DAILY CHECK
Every morning at 8am the system automatically scans all records and flags anything missing.
If your name is on the flag list — fix it before 10am.

---

## BOTTOM LINE
Airtable is how TMMT runs.
It is how decisions get made.
It is how money gets tracked.
It is how leads become customers.
Keep it updated. Every time. No exceptions.
