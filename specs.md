# Reputation + Mutual Credit Bot
## Federated Reputation and Mutual Credit System for Telegram

Version: 1.0  
Status: System Specification  
Architecture Target: Telegram Bot + PocketBase Backend

---

## 1. Purpose

This system provides:

1. A **global reputation registry** based on verified agreements and structured reviews.
2. A **group-deployable mutual credit system** with zero-interest credit lines.
3. Optional **federation between groups**, allowing inter-group trustlines and cross-group payments.
4. A neutral infrastructure layer usable by any Telegram group.

The system separates:

- Global identity and reputation
- Local group governance
- Local currencies and credit policies
- Inter-group trust relationships

---

## 2. Core Principles

### 2.1 Reputation Principles
- Reviews only exist for confirmed agreements.
- Reputation is tied to Telegram user ID.
- Reviews are factual and structured.
- Reputation is global and portable.

### 2.2 Mutual Credit Principles
- Money is created as mutual debt between participants.
- Total balances per group always sum to zero.
- Credit is issued as limits, not tokens.
- No interest is charged.

### 2.3 Governance Principles
- Groups control enforcement locally.
- Admin decisions are auditable.
- Reputation data is neutral infrastructure.
- No global bans enforced by the system.

---

## 3. System Architecture

### 3.1 Components

#### Telegram Bot
- Public bot interface
- Handles commands and workflows
- Enforces moderation actions
- Reads/writes to PocketBase

#### PocketBase Backend
- Data storage
- Admin UI
- Access rules
- Realtime subscriptions

#### Telegram Groups
- Optional integration
- Reputation warnings in configured topics
- Mutual credit enabled per group

---

## 4. Identity Model

Identity is defined by:

Telegram User ID (primary key)

Usernames are mutable labels and not identifiers.

Each member record includes:
- Telegram User ID
- Username (latest known)
- Display name
- Join timestamp
- Sanction status (per group)

---

## 5. Reputation System

### 5.1 Deal Lifecycle

1. User creates deal:

/deal @user

2. Both parties confirm.

3. Deal status becomes:

verified

4. After completion:

/review 

5. Each party may leave one review.

### 5.2 Review Rules

Reviews require:
- Verified deal
- One review per participant
- Structured fields only

Fields:
- outcome (completed | partial | cancelled | no_show)
- ratings (communication, reliability, quality)
- wouldWorkAgain (boolean)
- short note (length limited)

Evidence uploads are private.

### 5.3 Public Reputation Output

Visible:
- Verified deal count
- Average ratings
- Outcome counts
- Last activity date
- Review summaries

Hidden:
- Evidence
- Flags under investigation
- Admin notes

---

## 6. Group Integration

### 6.1 Bot in Groups

Any group admin may:
- Add bot
- Run setup
- Configure monitored topics

Bot capabilities:
- Reputation warnings in ad threads
- Admin enforcement commands
- Mutual credit transactions

### 6.2 Topic Monitoring

Admins define:
- Topic ID
- Category (gig, rental, housing, etc.)
- Warning thresholds
- Action levels

When users post:
- Bot checks reputation
- Posts trust card if thresholds met

---

## 7. Moderation and Sanctions

Sanctions are local to groups.

Types:
- warning
- mute
- temporary ban
- permanent ban

All actions recorded in audit logs.

Sanctions may:
- freeze mutual credit accounts
- reduce credit limits
- block ad posting

---

## 8. Mutual Credit System

### 8.1 Overview

Each group may deploy a mutual credit currency.

Characteristics:
- Zero-interest
- Credit limits instead of tokens
- Double-entry accounting
- Group-scoped ledger

Balances:

Sum(all balances in group) = 0

### 8.2 Account Behavior

Users may:
- Earn positive balance
- Spend into negative balance up to credit limit

Outgoing payments blocked if:

balance - payment < -creditLimit

### 8.3 Credit Line Assignment

Credit limits determined by:
- Verified deal count
- Reliability score
- Recency of activity
- Sanction status

Example policy:
- No verified deals → limit 0
- ≥1 verified deal → small limit
- Higher reliability → larger limits

Limits recomputed automatically.

---

## 9. Transactions

### 9.1 Payment Flow

/pay @user amount note

Process:
1. Check payer credit availability.
2. Create transaction.
3. Update balances.
4. Record ledger entries.
5. Post receipt.

Optional confirmation required above threshold.

### 9.2 Ledger Model

Double-entry:

payer:  -amount
payee:  +amount

Ledger entries immutable.

Reversals create compensating entries.

---

## 10. Federation Between Groups

### 10.1 Trustlines

Groups may extend trust to other groups.

Trustline defines:
- Maximum exposure allowed
- Directional credit limit
- Active/paused state

Trust is between groups, not individuals.

### 10.2 Cross-Group Payments

Payment routing:

User A (Group A)
↓
Group A trustline
↓
Group B trustline
↓
User B (Group B)

If no route exists, payment fails.

### 10.3 Federation Modes

#### Mode 1 — Same Unit
Multiple groups share same currency.

#### Mode 2 — FX Conversion
Groups maintain separate currencies with admin-defined exchange rates.

#### Mode 3 — Bridge Settlement
Bridge accounts maintain obligations between ledgers.

Default recommended: Mode 2.

---

## 11. Risk Controls

Required safeguards:

- Credit limits conservative by default
- Freeze on upheld serious flags
- Exposure caps between groups
- Automatic routing limits
- Audit trail for all admin actions
- Limit decay for inactivity

---

## 12. PocketBase Collections

### Core
- members
- deals
- reviews
- flags
- sanctions
- groups
- group_topics

### Mutual Credit
- mc_groups
- mc_accounts
- mc_transactions
- mc_entries
- mc_limits_history

### Federation
- mc_trustlines
- mc_fx_rates
- mc_crossgroup_transfers

---

## 13. Access Rules

Public:
- Reputation summaries only

Private:
- Evidence
- Flags
- Admin notes
- Ledger internals

Writes:
- Bot service account only

Admin moderation via PocketBase UI.

---

## 14. Safety Constraints

System must not:
- Allow anonymous reviews
- Allow reviews without verified deals
- Publish accusations or investigations
- Allow direct database writes by users

System must:
- Display sample sizes
- Maintain immutable ledger history
- Preserve auditability

---

## 15. Expected Outcomes

- Trust becomes portable across communities.
- Groups maintain autonomy.
- Reputation unlocks economic participation.
- Mutual credit circulates locally.
- Federation enables inter-community trade without centralized control.