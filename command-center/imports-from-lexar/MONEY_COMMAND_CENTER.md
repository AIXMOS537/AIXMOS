# Money Command Center

This system gives you one place to see bills, credit cards, expenses, cash flow, and money leaks across personal and business life.

## The Money Rule

Separate personal and business in the records, even if the money currently touches the same bank account.

Every transaction should have:

- Owner: Personal, Car Rentals, Credit Repair, Business Funding, Ecommerce, Shared
- Type: Income, Expense, Transfer, Debt Payment, Refund, Fee
- Status: Planned, Due, Paid, Overdue, Disputed, Cancelled
- Category
- Due date or transaction date
- Amount
- Payment account
- Notes
- Next action

## Tables You Need

Use the CSV files in `airtable_templates` to create these Airtable tables:

- `Bills`
- `Credit Cards`
- `Expenses`
- `Income`
- `Money Leaks`
- `Accounts`
- `Weekly Money Review`

## Daily Money Check

Ask AI every morning:

```text
Act as my money operator. Review my bills, cards, expenses, income, and money leaks. Tell me:

1. What is due in the next 7 days?
2. What is overdue?
3. Which cards are too high?
4. What expenses look unnecessary?
5. What business money is stuck?
6. What should I pay, pause, dispute, cancel, or follow up on today?
```

## Weekly Money Review

Ask AI every Sunday or Monday:

```text
Act as my CFO. Review my personal and business finances for the last 7 days.

Break down:
- income received
- expected income not received
- bills paid
- bills due soon
- overdue bills
- credit card balances
- card utilization risk
- expenses by category
- subscriptions to cancel
- business leaks
- personal spending leaks
- exact actions for the next 7 days
```

## Credit Card Control

Track each card with:

- Card name
- Personal or business
- Current balance
- Credit limit
- Utilization percentage
- Minimum payment
- Due date
- APR
- Autopay status
- Last payment date
- Strategy: Pay down, Use lightly, Freeze, Balance transfer, Dispute, Close later

Use this prompt:

```text
Review my credit cards. Rank them by urgency using due date, utilization, APR, minimum payment, and business importance. Tell me which card to pay first and why.
```

## Bill Control

Every bill should have an owner:

- Personal
- Car Rentals
- Credit Repair
- Business Funding
- Ecommerce
- Shared

Every bill should have a decision:

- Keep
- Reduce
- Cancel
- Renegotiate
- Move payment date
- Put on autopay
- Pause
- Dispute

Use this prompt:

```text
Review my bills and find savings. Tell me what to cancel, reduce, renegotiate, move, or keep. Separate personal from business.
```

## Expense Control

Every expense should be tagged by whether it helps revenue:

- Revenue producing
- Required operating cost
- Nice to have
- Waste
- Unknown

Use this prompt:

```text
Review my expenses and identify which ones are helping revenue and which ones are leaks. Give me a cut list and a keep list.
```

## Leak Categories

Track leaks like this:

- Missed follow-up
- Unpaid invoice
- Late fee
- Refund
- Cancelled booking
- Vehicle downtime
- Team delay
- Bad ad spend
- Subscription waste
- Credit card interest
- Overdraft or bank fee
- Inventory issue
- Customer service issue
- No-show
- Poor close rate

## Daily Money Dashboard Views

Create these views in Airtable:

- Due This Week
- Overdue
- High Card Utilization
- Expenses To Review
- Subscriptions
- Business Money Stuck
- Personal Bills
- Car Rental Cash Flow
- Credit Repair Cash Flow
- Funding Cash Flow
- Ecommerce Cash Flow

