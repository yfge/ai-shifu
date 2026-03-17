# Credits Billing Design

## Goal

Introduce a prepaid credits mechanism for creators on AI-Shifu:

- Creators recharge credits first.
- Credits are consumed by:
  - course authoring/generation done by the creator;
  - student learning/runtime usage on the creator's course.
- Deduction must be proportional to actual LLM and TTS usage.

This design intentionally builds on the existing usage metering layer instead of
creating a second independent charging pipeline.

## Existing foundation

The current codebase already has the right base primitives:

- `bill_usage` stores per-request and per-segment metering records for LLM/TTS.
  - File: `src/api/flaskr/service/metering/models.py`
- `record_llm_usage()` and `record_tts_usage()` already persist provider/model,
  token or character counts, request context, latency, scene, and billable flags.
  - File: `src/api/flaskr/service/metering/recorder.py`
- LLM calls already record actual token usage from LiteLLM responses.
  - File: `src/api/flaskr/api/llm/__init__.py`
- TTS flows already record request-level and segment-level usage.
  - Files:
    - `src/api/flaskr/service/tts/tts_usage_recorder.py`
    - `src/api/flaskr/service/learn/learn_funcs.py`
    - `src/api/flaskr/service/tts/streaming_tts.py`
- Courses already have an unambiguous owner/creator identity.
  - `created_user_bid` on shifu models
  - `get_shifu_creator_bid()`
- Payment/order infrastructure already exists, but it is course-purchase oriented.
  - File: `src/api/flaskr/service/order/models.py`

Conclusion: credits should be settled from `bill_usage` records, not from
controller-level business events.

## Core design decisions

### 1. Credits belong to the creator account

Credits are not learner-owned.

- When a creator authors a course, the creator's own balance is charged.
- When a student learns a creator's course, the same creator balance is charged.

This means every billable usage record needs two identities:

- `actor_user_bid`: who triggered the action
- `owner_user_bid`: whose credits should be charged

Examples:

- Creator previews a draft lesson:
  - `actor_user_bid = creator`
  - `owner_user_bid = creator`
- Student learns a published lesson:
  - `actor_user_bid = student`
  - `owner_user_bid = shifu.created_user_bid`

### 2. Billing settles only request-level usage

Do not charge from segment-level TTS records.

- `bill_usage.record_level = 0` is the billable settlement source.
- `bill_usage.record_level = 1` remains audit/debug detail only.

This avoids double charging and keeps the settlement rule simple.

### 3. Credits use integer micro-units

Do not store balances in float or decimal credits.

Use integer micro-credits:

- `1 credit = 1000 micro_credits`

Reasons:

- tiny token/char costs need deterministic rounding;
- ledger math must be exact;
- easier aggregation and refund logic.

### 4. Pricing is versioned and provider/model aware

Credit cost cannot be hardcoded in logic.

We need a pricing table keyed by:

- usage type: LLM / TTS
- provider
- model
- optional scene/business scene
- effective time range
- pricing version

## Proposed data model

### A. Credit account

New table: `billing_credit_accounts`

Purpose: current balance snapshot per creator.

Suggested fields:

- `account_bid`
- `user_bid` - creator user id, unique indexed
- `available_balance_micro`
- `locked_balance_micro`
- `total_recharged_micro`
- `total_consumed_micro`
- `status`
- `created_at`
- `updated_at`

### B. Credit ledger

New table: `billing_credit_ledger`

Purpose: immutable money/credit accounting trail.

Suggested fields:

- `ledger_bid`
- `account_bid`
- `user_bid`
- `entry_type`
  - `recharge`
  - `consume`
  - `refund`
  - `manual_adjust`
  - `freeze`
  - `release`
  - `expire`
- `delta_micro`
- `balance_after_micro`
- `source_type`
  - `credit_order`
  - `bill_usage`
  - `refund`
  - `admin`
- `source_bid`
- `usage_bid`
- `order_bid`
- `remark`
- `extra`
- `created_at`

Rules:

- one ledger row per balance change;
- never update business meaning after insert;
- refunds are compensating ledger rows, not row mutation.

### C. Credit pricing

New table: `billing_credit_prices`

Purpose: versioned pricing catalog.

Suggested fields:

- `price_bid`
- `status`
- `usage_type`
- `provider`
- `model`
- `business_scene`
- `unit_type`
  - `token`
  - `char`
- `input_rate_micro`
- `input_cache_rate_micro`
- `output_rate_micro`
- `minimum_charge_micro`
- `rounding_mode`
- `effective_from`
- `effective_to`
- `version`
- `extra`

Examples:

- LLM:
  - `cost = input * input_rate + input_cache * input_cache_rate + output * output_rate`
- TTS:
  - `cost = total_chars * output_rate`

### D. Extend usage settlement fields

Extend `bill_usage` instead of creating a second usage link table.

Recommended new columns on `bill_usage`:

- `actor_user_bid`
- `owner_user_bid`
- `business_scene`
  - `creator_authoring`
  - `creator_preview`
  - `student_learning`
  - `student_follow_up`
  - `system_internal`
- `credit_price_bid`
- `credit_version`
- `credit_cost_micro`
- `credit_status`
  - `pending`
  - `settled`
  - `waived`
  - `refunded`
  - `failed`
- `credit_ledger_bid`
- `settled_at`

Reason:

- billing remains traceable from the actual metered usage row;
- dashboard and cost analysis stay simple;
- reconciliation becomes direct.

### E. Recharge order

Do not overload the current course order shape too aggressively in V1.

The existing `order_orders` table is strongly course-centric:

- `shifu_bid`
- course purchase status assumptions
- current admin/reporting logic centers on course orders

Recommendation:

- add a dedicated `billing_credit_orders` table for creator recharge;
- reuse existing payment provider integrations and payment notification flow.

If later needed, a generic `order_type` refactor can unify course and credit orders,
but that should be a separate change.

## Charging flow

### 1. Recharge

1. Creator selects a recharge package or custom amount.
2. Create `billing_credit_order`.
3. After payment success:
   - create account if missing;
   - insert `billing_credit_ledger(entry_type=recharge)`;
   - increment `available_balance_micro`.

### 2. Authoring consumption

Billable creator actions include:

- draft preview generation;
- lesson content generation;
- teacher-side TTS generation;
- ask-provider preview/test actions.

Flow:

1. Resolve `owner_user_bid = actor_user_bid`.
2. Pass owner and business scene into `UsageContext`.
3. LLM/TTS call writes `bill_usage`.
4. Settlement service prices the row and inserts a `consume` ledger row.

### 3. Student learning consumption

Billable runtime actions include:

- lesson generation during study;
- follow-up ask flows;
- runtime TTS synthesis.

Flow:

1. Resolve `owner_user_bid = get_shifu_creator_bid(shifu_bid)`.
2. `actor_user_bid = student`.
3. Record actual LLM/TTS usage into `bill_usage`.
4. Settle from creator account.

### 4. Refund / reversal

Only refund credits when there is a clear business reason:

- failed payment compensation;
- duplicated settlement;
- explicit admin adjustment;
- fully rolled-back operation.

Mechanism:

- insert compensating `billing_credit_ledger(entry_type=refund)`;
- update `bill_usage.credit_status = refunded`.

## Runtime deduction strategy

### Recommended V1

Settle after actual usage is recorded, with creator-level balance check before entry.

Rules:

- before starting a billable action, check creator account balance against a
  configurable threshold;
- if below threshold, reject the action;
- after actual usage is recorded, deduct exact cost;
- settlement must run inside a per-owner lock to reduce overspend from concurrency.

This is the fastest path because it reuses the existing actual metering pipeline.

### Recommended V2

Add reservation/freeze for long-running streaming actions.

Use cases:

- very long student conversations;
- streaming TTS with many segments;
- concurrent learners on the same creator course.

Mechanism:

- reserve estimated max credits at request start via `freeze`;
- settle exact amount at completion;
- release unused reserved amount.

This is better for strict balance guarantees, but not necessary for initial launch.

## API changes

### Creator-facing APIs

New endpoints:

- `GET /api/billing/credits/account`
- `GET /api/billing/credits/ledger`
- `GET /api/billing/credits/prices`
- `POST /api/billing/credits/orders`
- `POST /api/billing/credits/orders/{order_bid}/pay`

Recommended dashboard additions:

- current balance
- consumed today / 7 days / 30 days
- cost split by:
  - authoring vs student learning
  - LLM vs TTS
  - provider/model
  - top consuming courses

### Internal settlement APIs

Not public at first.

Prefer service-layer functions:

- `settle_usage_credit(app, usage_bid)`
- `settle_pending_usage_for_owner(app, owner_user_bid, limit=...)`

## Code integration points

### A. Extend `UsageContext`

Add to `src/api/flaskr/service/metering/recorder.py`:

- `actor_user_bid`
- `owner_user_bid`
- `business_scene`

### B. Populate owner/actor in existing call sites

Main places:

- `src/api/flaskr/service/learn/context_v2.py`
- `src/api/flaskr/service/learn/learn_funcs.py`
- `src/api/flaskr/api/llm/__init__.py`
- `src/api/flaskr/service/tts/streaming_tts.py`

### C. Keep current preview/debug semantics separate

Current `usage_scene` means environment:

- debug
- preview
- production

Do not overload it with credit business semantics.

Instead:

- keep `usage_scene` for technical context;
- add `business_scene` for charging semantics.

### D. Dashboard/reporting reuse

The current metering summary endpoint and dashboard queries can be extended
instead of rebuilt:

- add credit cost aggregations from settled `bill_usage`;
- aggregate by `owner_user_bid` and `business_scene`.

## Pricing recommendation

### LLM

Charge by actual token usage:

- prompt/input tokens
- cached input tokens
- completion/output tokens

Do not use flat per-request pricing except as a minimum floor.

### TTS

Charge by actual synthesized text length.

Use:

- `total` or cleaned output chars as the primary basis

Keep `duration_ms` only for analytics/audit unless a provider demands
duration-based pricing.

### Package strategy

For creators, recharge UX should use credits packages, for example:

- Starter
- Growth
- Studio

But settlement should always be usage-based, not package-based.

Packages only determine how many credits are purchased and bonus ratios.

## Migration plan

### Phase 1

- add credit account / ledger / price tables
- extend `bill_usage` with owner/actor/credit settlement fields
- implement creator recharge order flow
- implement exact post-usage settlement
- expose creator balance and ledger APIs

### Phase 2

- dashboard credit analytics
- low-balance warnings
- per-course cost aggregation
- admin manual adjustment tools

### Phase 3

- credit reservation/freeze for long-running usage
- package promotions / bonus credits / expiration policies

## Open decisions

These should be fixed before implementation starts:

1. Should creator preview be billable from day 1, or only publish/runtime?
2. Should demo/system courses always be waived?
3. Should negative balances be allowed temporarily in V1?
4. Is a dedicated credit order table acceptable, or do we want a generic order refactor now?
5. What is the product-facing exchange rate between money and credits?
6. Do bonus credits expire while paid credits do not?

## Recommended implementation order

1. Extend metering context and `bill_usage` settlement fields.
2. Add credit account + ledger tables.
3. Add pricing table and settlement service.
4. Add recharge order flow.
5. Wire creator authoring and student runtime usage into owner-based charging.
6. Add dashboard and creator balance endpoints.
