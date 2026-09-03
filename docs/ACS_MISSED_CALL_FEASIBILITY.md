# Feasibility of the missed-call channel on Azure Communication Services

**Date:** 3 September 2026
**Author:** Aarush Pandit (23BIT0416)
**Status:** Mechanism confirmed viable. One architecture decision is blocked pending approval.

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

## 2. The problem this exposed, and it is not small

Microsoft's incoming-call guidance contains an explicit warning against the
hosting plan this project had already chosen:

> "Avoid hosting this endpoint on compute that scales to zero or has cold-start
> latency. For example, a serverless function app on a consumption-based plan can
> become dormant when there's no recent traffic. When an `IncomingCall` event then
> arrives at a cold instance, the time spent starting the host can consume the
> answer window, and the call goes unanswered."

Plan Section 17.3 lists **Functions on a consumption plan** among the services
deployed in Phase-II. For the daily outbound call that is fine: a timer trigger
has no deadline. For the **inbound** missed-call webhook it is not, and the
failure mode is exactly the one that destroys the project's credibility at
demonstration: the farmer rings number A to say he watered his field, the
Function is cold, the 30-second window expires, and the system silently loses the
only sensor reading it will ever get from that field that day.

The failure is also worst precisely when the system is least used, which is a
pilot with three farmers.

Microsoft's recommended alternatives, quoted:

- Azure App Service with Always On enabled
- Azure Functions on a plan that keeps always-ready (prewarmed) instances
- Azure Container Apps with a minimum replica count greater than zero
- Azure Kubernetes Service with sufficient baseline capacity

### Options

| Option | Effect on the pilot | Cost |
|---|---|---|
| **A. Split the app.** Timer-triggered planning stays on consumption; the inbound `acs_events` webhook moves to a small always-on host. | Correct behaviour where it matters, consumption billing where it does not. Two deployment units to manage. | One always-on instance. |
| **B. Whole Functions app on a Premium plan with one always-ready instance.** | Simplest to reason about and to deploy. | Premium plan floor, materially above consumption. |
| **C. Stay on consumption and accept the risk.** | Free, and wrong. A missed missed-call is an undetectable data loss, not a visible error. | None, but the accessibility claim in the report becomes unevidenced. |
| **D. Keep-warm ping.** A timer trigger every few minutes to prevent dormancy. | A widely used workaround, but Microsoft's guidance addresses cold start *and* reactive scale-out under a burst; a ping does not fix the second. | Negligible. | 

**Recommendation: A.** It preserves the consumption-plan economics the plan
argued for, confines the always-on cost to the one endpoint with a hard deadline,
and matches Microsoft's own guidance to "keep the path between the `IncomingCall`
event and the `AnswerCall` API short and direct".

**This decision costs money on Azure and is therefore not mine to take.** It is
raised here before the Functions app is built, rather than after, because the
choice determines the deployment layout of `src/azure/functions/` and the Bicep
in M5.

---

## 3. Consequences already absorbed into the M3 design

These do not need a ruling and are being implemented now.

**Idempotency is mandatory, not defensive.** Because delivery is at-least-once, a
replayed `WATER_GIVEN` event would credit the water balance twice and silently
under-irrigate the field for the rest of the interval. Every event carries a
deduplication key of caller number, number called and IST date, and the handler
rejects a repeat. Unit-tested as a no-op.

**Event Grid retry settings must be tuned.** Microsoft recommends Max Event
Delivery Attempts of 2 and Event Time to Live of 1 minute for `IncomingCall`,
because a call that has stopped ringing cannot be usefully retried. This goes
into the M5 Bicep.

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
