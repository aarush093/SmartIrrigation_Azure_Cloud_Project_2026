# Phase-II supplementary reading

**Supplementary. Outside the fifteen mandated papers, which are unchanged.**

Added 5 September 2026 by Aarush Pandit (23BIT0416). The fifteen-paper survey in
[`literature_survey.md`](literature_survey.md) and the three per-student gap
analyses are a submitted record and are not edited.

Phase-II sharpened the project's claim from "translation and delivery" to
"pump minutes inside a rationed electricity window, delivered by voice and
missed call". That sharpening rests on evidence the original fifteen papers do
not cover, because it is economics, energy policy and ICT-for-development rather
than irrigation modelling. Those sources are recorded here so the claim is
traceable.

---

## Why the constraint exists: agricultural power rationing in India

**R1.** *Removing rationing: power consumption and groundwater monitoring in
South India.* Journal of Environmental Economics and Management, 2025.
<https://www.sciencedirect.com/science/article/abs/pii/S0095069625001287>
`TODO [VERIFY]` authors and volume for IEEE citation.

> Agricultural electricity in most Indian states is unmetered and rationed
> through limited daily supply hours. Erratic and unannounced supply pushes
> farmers toward over-irrigation of water-intensive crops.

This is the mechanism the project's novelty addresses. It is also, notably, the
mechanism the Objective 6 simulation reproduced: the scheduler applies more water
than an unconstrained trigger would, precisely because it cannot rely on the next
window.

**R2.** *Efficient irrigation and water conservation: evidence from South
India.* Journal of Development Economics, 2023.
<https://www.sciencedirect.com/science/article/abs/pii/S0304387823000068>
`TODO [VERIFY]` authors and volume.

Where power is free at the margin but rationed to a few hours a day, farmers
maximise pumping whenever supply arrives rather than conserving water. A farmer
behaving this way is behaving rationally, which is why an advisory that ignores
the window is ignored in turn.

**R3.** Asian Development Bank, *Maharashtra Power Distribution Enhancement
Program for Agricultural Solarization*, project 58396-001.
<https://www.adb.org/projects/58396-001/main>

Maharashtra agricultural consumers receive power at fixed hours, mostly at
night, on a rotating schedule. This is the Beed pilot farmer's situation, and the
daytime solar feeder in the demonstration comes from this programme.

**R4.** *Making agriculture sustainable: solarising farm feeders*, 2019.
Grey literature; used only as supporting context.
<https://www.linkedin.com/pulse/making-agriculture-sustainable-solarising-farm-feeders-saurabh-kumar>

Night supply leads to pumps left running all night; an area irrigable in one day
takes four to five nights.

---

## That the windows are published, and therefore usable as an input

**R5.** MSEDCL, *Letter to field: AgLM time schedule, May to June 2026*,
30 April 2026.
<https://www.mahadiscom.in/wp-content/uploads/2026/04/Letter-to-field_AGLM-time-Sch_May26-June26_30.04.2026.pdf>
Fixes 8-hour daytime supply on agricultural feeders, staggered between 07:30 and
17:30.

**R6.** MSEDCL time schedule circular, 1 October 2020, with a substation-wise
annexure of 8-hour windows such as 06:00 to 14:00 and 10:00 to 18:00.
`TODO [VERIFY]` original mahadiscom.in link.

**R7.** *PSPCL substantially increases power supply to agricultural feeders*,
PSU Watch, July 2026.
<https://psuwatch.com/newsupdates/pspcl-substantially-increases-power-supply-to-agri-feeders>
Punjab schedules 8 hours on agricultural feeders during paddy season. This is the
Ludhiana pilot farmer's situation.

**R8.** *With segregated feeders, UPPCL plans 10-hr power to farmers.*
Hindustan Times, Lucknow, 18 November 2018. Uttar Pradesh segregated feeders
supply 07:00 to 17:00.

**Why these matter.** R5 to R8 establish that the window is *published data*, not
something the project would have to sense. That is what makes a zero-hardware
design possible: the schedule is a document, and Azure AI Document Intelligence
can read it.

---

## What is closest, and why none of it does this

Full comparison table in `docs/PHASE2_NOVELTY_AND_PLAN.md` Section 3. The two
groups that come nearest:

**Energy-aware irrigation optimisation.** R9 (Agricultural Water Management,
2018) minimises energy use in a collective pumping station under time-of-use
tariffs; R10 (Energy, 2021) and R11 (Journal of Energy Storage, 2024) schedule
agricultural microgrids day-ahead. All three are **grid-side or estate-side
tools** for an operator with control of the supply. None is farmer-facing, and
none addresses a smallholder who has no control over anything except when he
turns his own pump on.

**Farmer-facing advisories.** Kissan-Dost (R12, 2026) gives qualitative advice
over WhatsApp with an LLM and needs about USD 140 of on-farm hardware.
Farmer.Chat (R13, 2024) answers questions and gives no quantity. FarmChat (R14,
2018) and Avaaj Otalo (R15, 2010) are conversational and advisory. The IWMI/eLEAF
SMS service (R16, 2014) gives a daily water balance but is text-only and
power-blind. A 2026 smartphone soil-water-balance app (R17) computes net and
gross requirements but assumes a smartphone and power on demand.

**The gap is the intersection.** Nothing found is simultaneously farmer-facing,
quantitative, power-window-aware, and usable without literacy or a smartphone.
The claim of novelty is made relative to a search of Google Scholar,
ScienceDirect, MDPI, IEEE Xplore, arXiv and ICT-for-agriculture grey literature
in August and September 2026, and is worded that way in every document.

---

## Why the channel is a missed call rather than an app or a keypress

**R18.** IDinsight, *IVR and text message interventions to provide fertilizer
information to farmers: experiments from India*, 2019.
<https://medium.com/idinsight-blog/ivr-and-text-message-interventions-to-provide-fertilizer-information-to-farmers-16e651402be6>

Found **very low response to keypress prompts**. This is why the missed call is
the primary channel in this design and the keypress question is only the fallback
asked when no missed call arrived.

**R19.** ICTworks, *When is the best time to send IVR and SMS messages to
farmers?*, 2022. <https://www.ictworks.org/send-ivr-sms-messages-farmers/>

Evening calls were answered best. This is the source of the 18:00 to 20:00
preferred calling slot in the quiet-hours rule.

---

## Sources for the constants, distinct from the argument

Recorded here because they are cited throughout the code and belong in one
place, though they are references rather than related work.

- **R20.** Allen, Pereira, Raes and Smith, *Crop evapotranspiration*, FAO
  Irrigation and Drainage Paper 56, 1998. Tables 11, 12 and 22, and Example 18,
  which the ET₀ implementation is verified against.
- **R21.** Saxton and Rawls, *Soil water characteristic estimates by texture and
  organic matter*, SSSAJ 70(5), 2006. The pedotransfer functions.
- **R22.** Brouwer, Prins and Heibloem, *Irrigation Water Management: Training
  Manual No. 4*, FAO, 1989. Application efficiencies.
- **R24.** Doorenbos and Kassam, *Yield response to water*, FAO Irrigation and
  Drainage Paper 33, 1979. **The source of Ky, which does not appear in FAO-56.**
- **R25.** Steduto, Hsiao, Fereres and Raes, *Crop yield response to water*, FAO
  Irrigation and Drainage Paper 66, 2012. Updated stage-wise Ky.

R24 and R25 were added after an error was caught: the build brief attributed Ky
to FAO-56 along with the stage lengths, Kc, Zr and p, which are correctly sourced
there. Ky is not in FAO-56 at all. The correction and its trail are in
`docs/PHASE2_BUILD_LOG.md`.
