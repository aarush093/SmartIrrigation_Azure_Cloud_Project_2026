# Review-2 viva notes

**Prepared by:** Aarush Pandit (23BIT0416), 5 September 2026
**Scope:** Phase-II, milestones M0 to M6.

Every number here traces to a file under `results/`. If a question needs a
figure that is not in this document, the answer is "let me show you the file"
rather than a guess.

---

## The six questions that will certainly be asked

### 1. Why did the project narrow, and does that not weaken the original novelty?

It extends it rather than replacing it.

Phase-I named the gap as **translation and delivery**: turning free forecast,
reanalysis and soil data into a specific instruction, through a channel the
farmer already uses. Phase-II fixes both halves of that gap rather than
substituting a new one.

The **translation target** becomes pump minutes inside the farmer's rationed
electricity window. Existing advisories answer *when does the crop need water*.
For a farmer on a rationed feeder, the binding question is *when can the pump run
at all*. Telling him to irrigate on Tuesday afternoon when his feeder is live on
Tuesday night is agronomically correct and operationally useless.

The **delivery channel** becomes a voice call plus three missed-call numbers,
which needs no literacy, no smartphone and no data pack.

Both Phase-I objectives, all six of them, are retained with their original
acceptance criteria. Two are reported as not met at their stated thresholds, with
the measurement, rather than being adjusted to fit. The reconciliation is
Section 17 of `docs/PHASE2_NOVELTY_AND_PLAN.md`.

### 2. Why no on-farm hardware, and what do the missed calls replace?

Because hardware is what stops these systems reaching the farms that need them.
The nearest comparable system in our search, Kissan-Dost, needs about USD 140 of
equipment per farm. On a half-hectare holding that cost is the whole objection.

Three inputs a sensor would normally provide, and where each comes from instead:

| Would need hardware | Comes from |
|---|---|
| Soil moisture | FAO-56 water balance driven by free forecast data |
| Soil type | **One question at onboarding**, three icon choices, answered by the farmer about his own field |
| Pump discharge | A bucket and a watch, timed once at onboarding |

And the feedback a controller would provide comes from **three missed calls**:
ring A for *water given*, B for *power did not come*, C for *say today's plan
again*. Each is free to the farmer because the platform rejects the call without
answering it, so it never connects and is never billed.

The missed call is the only sensor this system has. That is why idempotency is
enforced in the database rather than in memory: a replayed event would credit the
water balance twice and silently under-irrigate that field for the rest of the
interval, with no error anywhere to notice it.

### 3. Why are pump minutes spoken as clock times, with no digits?

Two reasons, and they compound.

A farmer who cannot read does not know whether **"6:00"** is morning or evening.
The single most important string the system produces would have carried the most
ambiguity. And a text-to-speech engine handed a numeral renders it
unpredictably across languages.

More basically, **"run the pump for 409 minutes" is not actionable.** He cannot
convert it, and if the window opens at 22:00 he will be asleep long before it
matters. So the script gives a start time and a stop time, spoken in words with
the part of day attached:

> *राम काका, नमस्ते। बिजली रात दस बजे से सुबह छह बजे तक है। … रात दस बजे पंप चालू
> करो, और सुबह पौने पाँच बजे बंद कर दो। खेत सूखा है।*

The stop time rounds down to five minutes, never up, so a truncated run is never
overrun and the pump is never asked to draw power that has already gone.

**No digit appears in any farmer-facing script, in any script system** —
checked across ASCII, Devanagari and Tamil numerals by
`tests/test_scripts.py::TestNoTechnicalUnitsLeak`, over nine schedule states in
three languages. That test is the evidence behind the accessibility claim, and it
is checkable in one command.

### 4. Objective 2 is not met. Why report it as an uncertainty budget?

Because the threshold turned out to be the least informative thing about the
measurement.

The criterion is ET₀ within 0.2 mm/day. Measured over **1,095 station-days**:
**MAE 0.279 mm/day, bias +0.065**. Not met, and reported as measured.

Four things put that number in context, in the order they were established:

1. **The implementation is verified correct.** It reproduces every printed
   intermediate of FAO-56 Example 18 — P, γ, Δ, e°(Tmax), e°(Tmin), es, ea, Ra,
   Rso, Rns, Rnl, Rn and the final 3.9 mm/day.
2. **It is not an hourly-versus-daily artefact.** FAO-56 equation 53 was
   implemented and summed over 24 hours; the hourly sum is *worse*, 0.368 against
   0.154 at Beed. That hypothesis is dead, not merely unproven.
3. **The residual is smaller than the disagreement between the input datasets.**
   Our own identical implementation, fed Open-Meteo (ERA5) and NASA POWER
   (MERRA-2) inputs, disagrees with itself by **0.735 mm/day**, 2.6 times the
   residual.
4. **It costs almost nothing to the farmer.** Propagated to pump minutes, the
   overall bias costs **8.6 minutes of a 409-minute run, 2.1%**. Application
   efficiency alone spans **129 minutes** on the same field, and an uncalibrated
   pump discharge spans 102.

**The strongest sentence the objective produced:**

> *This implementation agrees with an independent FAO-56 implementation more
> closely than two reanalysis datasets agree with each other.*

*Caveat to volunteer before it is asked:* the two products are on different
grids, POWER at 0.5° × 0.625° against ERA5 at 0.25°, so part of the 0.735 is
grid mismatch. The conclusion holds regardless: even a substantial discount
leaves it above 0.279.

### 5. Why is there no live phone number, and what is the production route?

Two independent blockers in Microsoft's own documentation, either one decisive:

1. **India is not in the country and region list** for Communication Services
   telephone numbers.
2. **Numbers cannot be acquired on trial accounts or with Azure free credits**,
   and availability is restricted to subscriptions with a billing address in a
   supported region.

ACS SMS is documented as United States only, so the Phase-I text fallback is
blocked by the same restriction.

**This changes nothing about what runs, and that is not luck.** Plan Section 15
listed number availability as a risk with the mitigation "build behind an
adapter; demo with the simulated telephony console", and that mitigation was
implemented before the blocker was confirmed. `SimulatedTelephony` drives the
complete daily loop — forecast, soil, balance, scheduling, three languages,
speech, the call, and all three missed-call events — with no phone number, no ACS
resource and no credit spent.

`AcsCallAutomationTelephony` is written and tested against the documented API:
the `IncomingCall` event shape, the pre-answer availability of the caller number,
the `Reject` action, subscription validation and at-least-once delivery. It is
the evidence the integration was designed properly.

**Production route:** an Indian CPaaS under TRAI DLT registration — Exotel,
Gupshup, Kaleyra, or Twilio's India offering — as a new `TelephonyAdapter`
implementation and a configuration change. Not a redesign: the engine, scheduler,
scripts, state machine and Functions app are unchanged, because none of them
knows which adapter it is talking to.

### 6. What did Objective 6 measure, against which baseline, and why that one?

**The baseline is the answer to this question.**

An unconstrained FAO-56 trigger assumes the pump can run whenever the crop wants
water. That is physically impossible on a rationed feeder, so beating it is not
this project's claim and losing to it would mean nothing. It is kept in the table
as **Pref**, explicitly labelled physically unachievable.

The real baseline is **P1: a correct agronomic instruction the farmer can only
execute when the power arrives.** That is exactly what a farmer using any
existing advisory app experiences today.

Five policies, two seasons. Nine fields were simulated; the headline is the
**six non-ponded** ones. Rice is excluded because `params/crops.yaml` already
states a depletion-triggered balance is the wrong model for ponded paddy — say
this before you are asked, and have the all-nine figure ready.

| Policy | Water (mm) | Stress days | Percolation (mm) |
|---|---:|---:|---:|
| P0 calendar | 6,362 | 631 | 7,605 |
| **P1 advisory, power constrained** | **4,435** | **576** | **4,212** |
| P2 power-window scheduler | 5,873 | 95 | 4,992 |
| P3 scheduler + rain skip | 5,740 | 96 | 4,859 |
| *Pref unlimited power (unachievable)* | *5,048* | *116* | *4,431* |

**Objective 6 as written is not met.** It asks for 20% less water than
fixed-interval; P3 applies **9.8% less** — right direction, short of the
threshold. Reported as measured. All nine fields: 6.6% less.

**The novelty claim, P3 against P1 under an identical power constraint:
83.3% fewer stress days at 29.4% higher water use.** All nine: 57.3% fewer
stress days at 18.3% higher water use. Both sets support the same conclusion.

The scheduler buys reliability with water, and the mechanism is visible in the
policy: it cannot rely on the next window arriving, so it refills early. That
keeps the root zone fuller, which is why stress nearly disappears and why more
of the rain that follows drains below it.

**The number no one else can produce:** P3 against Pref isolates the constraint
itself, since the two differ only in whether power is available on demand.
**13.7% more water.** That is the measured price a smallholder pays for a
rationed feeder, and it is available only because this system models the window
explicitly. P3 reaches *fewer* stress days than Pref, 96 against 116, which is
not a paradox: Pref waits for depletion to reach RAW, while P3's capacity-limit
branch refills before the deficit outgrows one window. Pref bounds what
unlimited power buys, not what perfect agronomy would.

### If you are asked whether the numbers changed

They did, once, and you should say so plainly rather than be caught by the git
history. The first run reported P3 applying 13.8% **more** water than
fixed-interval. That was a **carry-over double count in the scheduler**:
`plan_day` asked for `depletion + carry_over`, while the water balance was
stepped with the depth actually delivered, so the shortfall of a truncated run
was inside the depletion *and* added on top of it the next morning.

It was caught by a physical inconsistency, not by a test: the constrained policy
was applying 2,041 mm more water than the *unconstrained* one, with 91% of the
excess draining below the root zone. A policy cannot apply more than the ideal
unless it is over-filling.

What to say: the defect was in the engine as well as the simulation, so a real
farmer would have been told to over-irrigate the morning after every truncated
run; it is fixed, it has a regression test that fails against the old code, the
before-and-after measurement is in `results/README.md`, and the superseded
figures are retained in the build log rather than deleted.

**Do not present this as a near miss.** Present it as the reason the result is
now trustworthy: a number that survives a physical sanity check is worth more
than one that was never checked.

### If you are asked about the rain skip

It barely matters, and the sensitivity table says so. Across confidence
thresholds 0.5 to 0.8 the water applied moves 87 mm out of 5,750 — under 2% —
while the skips issued nearly triple. The power-window scheduling accounts for
1,305 mm against the same baseline. **The value is in the scheduling, not the
skip.** Volunteering this is stronger than defending a threshold.

---

## Per module: three likely questions each

### Engine, FAO-56

**Q. How do you know the water balance is right?**
FAO-56 equation 85 with deep percolation from equation 88, and a conservation
test asserting that over any sequence, inputs minus outputs equals the change in
depletion to floating-point tolerance. The test asserts the sequence never
touches a bound, so no clamping can mask a leak.

**Q. Your crop constants — where are they from, and are they verified?**
Every one is in `params/crops.yaml` with its source cited, and verification is
recorded **per field**. Kc, Zr and p were checked against printed FAO-56 Tables
12 and 22. Stage lengths are verified only for wheat and maize, the two crops
with printed Indian rows in Table 11; the rest carry a non-Indian region and stay
unverified. Ky stays unverified because it is not in FAO-56 at all — it is FAO-33
with FAO-66 updates, and the build brief originally mis-attributed it. That
correction, and the fact that a subsequent "correction" of cotton's Kc_ini was
itself wrong, are both recorded in the build log.

**Q. Why is Saxton-Rawls not fully implemented?**
The density adjustment is not applied, and the module says so. A first draft
contained one that derived the "normal" density from the measured bulk density,
making the ratio identically 1.0 at every input — an adjustment that appears to
run and does nothing. It was removed rather than left in, and the correct version
needs equations 3 to 5, which are carried as `TODO [VERIFY]`.

### Scheduler

**Q. What is the actual novelty, in one sentence?**
The DISCOM feeder window is a first-class scheduling constraint: the
recommendation names the window and the pump minutes inside it, and a
capacity-constrained refill acts *before* the deficit outgrows what one window
can repay.

**Q. Why does the capacity branch look at the next window rather than today?**
Because refilling only once the deficit has already outgrown one window is too
late. The branch was originally specified as `D >= C` and corrected to
`D_next > C`. The test asserts its own precondition — that today's deficit is
still inside one window's capacity — so it would fail against the superseded rule
rather than passing by accident.

**Q. How do you know it never schedules something impossible?**
Hypothesis property tests over hundreds of generated inputs: scheduled minutes
never exceed the window; allocated minutes across all fields on one pump never
exceed it; delivered depth plus carry-over always equals the requirement;
identical inputs always give identical schedules. `plan_day` reads no clock and
no random number.

### Channel

**Q. How does a missed call cost the farmer nothing?**
Event Grid delivers `IncomingCall` on ring, with the caller number populated
before any answer. The application calls `Reject`, so the call never connects and
there is nothing to bill. If the host is cold and the rejection misses the
30-second window, the call simply rings out and the event still arrives — nothing
is lost either way, which is why a consumption plan is adequate.

**Q. What happens if the same event arrives twice?**
Nothing. Event Grid delivers at least once. The deduplication key is caller,
number called, and the **operational date**, and it is the Cosmos document id, so
a replay fails on the uniqueness constraint. The operational day rolls over at
06:00 IST, not midnight, because a 22:00-to-06:00 night feeder means a farmer
ringing at 00:30 is reporting the same irrigation as one ringing at 23:30. That
bug was found by a test, not by inspection.

**Q. What if only one toll-free number can be provisioned?**
Single-number mode is a first-class configuration. That number means *water
given*, and a power failure is inferred from its absence **together with** an
explicit "no" to the next day's question. Absence alone is not enough: a farmer
who forgot to ring looks identical to a failed feeder, and lowering a feeder's
reliability on that evidence would degrade every schedule in the village.

### Azure

**Q. Objective 5 requires private endpoints. You have none.**
It requires private endpoints **or authenticated gateways**. Private endpoints
carry a per-endpoint hourly charge that exceeds the remaining student credit, so
the requirement is met the other way: Cosmos DB with local authentication
disabled and managed identity only, Key Vault with RBAC, API Management in front
of the operator endpoints, Entra ID on them, and gitleaks in CI over full history.
VNet is deferred to Phase-III with that stated.

**Q. Nine Phase-I services are missing.**
None is removed; each is deferred with a named substitute meeting the same need
at pilot scale — Storage Queues for Service Bus, Cosmos continuous backup for
Backup vault, Blob with a TTL for Redis, a Functions timer for Data Factory. The
full table is `docs/AZURE_SERVICES_PHASE2.md`.

**Q. Has any of it been deployed?**
No. The Bicep compiles cleanly to 25 resource declarations and `make deploy-plan`
runs `what-if` only. No credit has been spent. Everything is on a free or
consumption tier, with the tier and the reason in a comment on each resource.

### AI/ML

**Q. Objective 3 is not delivered.**
It is Krishna Agrawal's module and is in progress. It is deliberately off the
critical path: the scheduler depends on a `MoistureForecaster` protocol whose
default implementation is ETc = Kc × ET₀ and always works. If the learned model
misses 0.80, the fallback stays active and nothing downstream changes.

**Q. How do you know the simulation is not cheating?**
The water balance uses observed archive weather, but every *decision* uses the
forecast **as it was issued that morning**, from the Open-Meteo Previous Runs
API, which reaches back beyond both simulated seasons. Had the skip rule read the
archive it would have been skipping on rain it already knew had fallen.

**Q. Does the rain calibration actually help?**
It beats the raw forecast on Brier score, **0.0859 against 0.1174** over 4,344
held-out pairs, fitted on the earlier season and scored on the later one. But its
effect on the outcome is small: P3 saves only 1.2% of water over P2, because at
the 0.7 confidence threshold the calibrated probability rarely clears the bar.
That is the conservative direction by design — a wrongly skipped irrigation costs
the crop, a needless one costs only water — but it means **the value of this
system is in the scheduling, not the skip**, and the results say so.

---

## Things to volunteer rather than be caught on

- Objectives 2 and 6 are **not met** at their stated thresholds. Say so first.
- The Hindi and Tamil masters have **not** been checked by a native speaker.
  `results/script_samples.txt` exists for exactly that review.
- Indian stage lengths and all Ky values are **unverified** and marked in the
  parameter file.
- **No live phone call has ever been placed.** The channel is demonstrated on the
  simulated console.
- Two of the six objectives depend on a teammate's module that is still in
  progress.
- A "correction" made during this work was itself wrong — cotton's Kc_ini — and
  the trail is in the build log rather than tidied away.
