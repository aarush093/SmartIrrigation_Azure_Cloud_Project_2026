# Feasibility of the missed-call channel on Azure Communication Services

**Date:** 3 September 2026
**Author:** Aarush Pandit (23BIT0416)
**Status:** Mechanism confirmed viable. Hosting decided: consumption plan (Decision 1, section 3).

The entire illiteracy-first design rests on one assumption: that an inbound call
can be detected and refused *without being answered*, so that the farmer is never
charged and the missed call itself carries the information. If that assumption
were false, the channel would need redesigning. This document records the
verification, performed before any code was written against it, and the one
problem it exposed.

Sources, both read directly:

- [Incoming call concepts](https://learn.microsoft.com/en-us/azure/communication-services/concepts/call-automation/incoming-call-notification)
- [Call Automation overview](https://learn.microsoft.com/en-us/azure/communication-services/concepts/call-automation/call-automation)

---

## 1. The mechanism works

| Question | Answer |
|---|---|
| Is there an inbound notification? | Yes. Event Grid delivers `Microsoft.Communication.IncomingCall` when a call reaches a PSTN number owned by the ACS resource. |
| Is the caller's number available before answering? | Yes. The payload carries `data.from` and `data.to`, each with a `PhoneNumber.Value`. Microsoft's own documented example filters an Event Grid subscription on `data.to.PhoneNumber.Value`, which is only possible if the field is populated before any answer. |
| Can the call be refused without answering? | Yes. **Reject** is a documented pre-call action, supported in the Python SDK: "your application can receive the `IncomingCall` event and prevent the call from being connected to the destination endpoint." |
| Is the caller charged? | The call is never connected, so no call is established to bill. **TODO [VERIFY]** against the ACS PSTN pricing page before the pilot: confirm no inbound charge accrues for a rejected call. |
| How long is there to respond? | The call rings for **30 seconds**. After that the window has closed. |
| Are events delivered exactly once? | **No. At least once.** Microsoft states plainly: "Event Grid delivers events at least once, so your application can receive the same `IncomingCall` event more than once." |

**Conclusion: the three-number missed-call vocabulary in plan Section 5.3 is
implementable as designed.** The farmer rings number A, B or C; Event Grid
reports which number was called and who called it; the application rejects the
call and records the event. No answer, no connection, no charge to the farmer.

One refinement over the original design. The plan assumed the farmer hangs up
before the call is answered, which is the ordinary Indian missed-call idiom.
Rejecting is better: it is deterministic and immediate rather than depending on
how long the farmer holds, and it frees the line at once.

One documented limitation, harmless here: "Web hook callback events only
communicate the `answer` pre-call action, not for `reject` or `redirect`." A
rejected call therefore produces no Call Automation webhook. That is fine,
because the Event Grid `IncomingCall` event is itself the record, and it has
already arrived.

---

## 2. The cold-start constraint, and why it does not bind here

Microsoft's incoming-call guidance warns against hosting the webhook on compute
that scales to zero:

> "Avoid hosting this endpoint on compute that scales to zero or has cold-start
> latency. For example, a serverless function app on a consumption-based plan can
> become dormant when there's no recent traffic. When an `IncomingCall` event then
> arrives at a cold instance, the time spent starting the host can consume the
> answer window, and the call goes unanswered."

**That warning is written for applications that must answer the call**, which is
how an ordinary IVR works: the 30-second ring is a hard deadline because a call
not answered inside it is a customer lost.

**This design never answers.** The success state for a missed call is precisely
that the call is *not* connected. Working through what a cold start actually
costs:

| | Warm Function | Cold Function |
|---|---|---|
| What happens to the call | `Reject` fires, the call ends immediately | No `Reject` in time, the call rings out unanswered |
| What happens to the event | Event Grid delivers it | Event Grid delivers it, a few seconds later |
| Sensor reading | Recorded | Recorded |

The `IncomingCall` event goes to Event Grid, not to the call, and Event Grid
delivers and retries independently of whether the ring window is still open.
Both paths end with the call unconnected and the event recorded. The cold path is
slower and less tidy; **neither loses the reading**. A missed-call event that
lands twenty seconds late is worth exactly as much as one that lands instantly,
because what it updates is a daily water balance.

The 30-second answer window is therefore not a binding constraint on this
channel. An earlier draft of this document treated it as one and recommended
buying always-on compute to satisfy it. That was an error of reasoning:
importing a constraint from the answer-the-call scenario without checking whether
it binds here. Buying warm compute for a flow that never answers would also be
indefensible at review, and correctly so.

## 3. Decisions

### Decision 1: consumption plan, single Functions app

`function_app.py` at the deployment root, no split, as plan Section 17.3 already
specified. Cheaper and more defensible than the alternative.

`Reject` remains the action taken on `IncomingCall`. It is instant and
deterministic when the host is warm, and ringing out is a correct fallback when
it is not.

**Phase-III upgrade path**, if the pilot ever shows a need for guaranteed instant
rejection: move only the `acs_events` webhook to always-on compute (App Service
with Always On, or Functions on a plan with pre-warmed instances), leaving the
timer-triggered planning on consumption. Nothing in the M3 design forecloses
that; the webhook is already a separate trigger.

**To be measured during the pilot:** the observed share of inbound calls that
receive an instant `Reject` versus those that ring out. A documented limitation
with a number behind it is a strong review answer; an unexamined one is not.

### Decision 2: retry generously, and dead-letter, which reverses Microsoft's guidance

Microsoft recommends Max Event Delivery Attempts of 2 and Event Time to Live of 1
minute for `IncomingCall`, because in the answer-the-call scenario a late event is
useless and dropping it quickly is right.

**For this design the opposite holds.** A late event is still a valid field
observation, and it may be the only one that field produces that day. Dropping it
after a minute would discard the reading to save nothing.

The Event Grid subscription is therefore configured with:

- Event Time to Live measured in **hours**, not one minute
- the **default** delivery attempt count, not 2
- a **dead-letter destination in Blob Storage**, so an event that ultimately
  fails delivery is preserved rather than lost silently

### Decision 3: a keep-warm timer, as comfort and not as correctness

A five-minute timer trigger costs effectively nothing on consumption and raises
the share of calls that receive an instant `Reject`.

**Correctness must not depend on it.** A test asserts the handler behaves
identically whether the event arrives during the ring or a minute afterwards, so
that removing the timer changes cost and tidiness but never outcome.

### Decision 4: confirmation is carried on the next call, not on a new one

Neither path gives the farmer any feedback that his missed call registered: a
rejected call and a rung-out call sound much the same to him. Adding a
confirmation call or SMS would cost money on every event and add a second thing
that can fail.

Instead the **next scheduled call opens by acknowledging it**: "kal aapne bataya
tha ki paani de diya". Zero marginal cost, carried on a call that was happening
anyway, and it gives him the chance to correct us if we logged the wrong thing.
Implemented as an optional opening clause in ``speak_schedule``.

## 3. Consequences already absorbed into the M3 design

These do not need a ruling and are being implemented now.

**Idempotency is mandatory, not defensive.** Because delivery is at-least-once, a
replayed `WATER_GIVEN` event would credit the water balance twice and silently
under-irrigate the field for the rest of the interval. Every event carries a
deduplication key of caller number, number called and IST date, and the handler
rejects a repeat. Unit-tested as a no-op.

**Event Grid retry settings must be tuned, in the opposite direction to
Microsoft's default advice.** See Decision 2. Generous TTL, default attempt
count, dead-letter to Blob Storage. This goes into the M5 Bicep.

**The webhook must be filtered.** Without an Event Grid subscription filter the
application receives duplicate `IncomingCall` events for redirect scenarios, and
Microsoft warns this "can result in infinite loops". The subscription filters on
`data.to.PhoneNumber.Value` against the provisioned numbers.

**Subscription validation must be handled.** Event Grid requires the webhook to
answer a `SubscriptionValidationEvent` before it will deliver anything.

**Degraded single-number mode is built regardless.** Only one number may be
provisioned in time for the pilot. In that mode the single number means "paani de
diya", and a power failure is inferred from the absence of that call together
with the next day's confirmation question. The demo runs in either mode.

---

## 4. Outstanding verification before the pilot

- `TODO [VERIFY]` ACS PSTN number availability for India, and whether inbound
  Indian numbers can be provisioned on the student subscription at all.
- `TODO [VERIFY]` that a rejected inbound call accrues no charge, to the farmer
  or to us, against the current ACS pricing page.
- `TODO [VERIFY]` TRAI TCCCPR 2018 position on consented transactional automated
  calls, and permitted calling hours.
