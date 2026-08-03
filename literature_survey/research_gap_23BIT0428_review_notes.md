> \# Research Gap Review Notes for Papers 11 to 15
>
> Student C: Krishna Agrawal (23BIT0428)
> Project: Cloud-Based Smart Irrigation Recommendation using Weather Intelligence
>
> \## Purpose of this file
>
> Working notes kept alongside the formal research gap analysis. These record how the five assigned papers were read, which claims were checked against the published record and which limitations were judged most relevant to our irrigation use case.
>
> \## Reading order and rationale
>
> Papers 11 to 15 were read in order of decreasing scope, starting with the broadest system level studies before the narrower model level ones. This made it easier to separate limitations that are architectural from those that are purely algorithmic.
>
> \## Cross cutting observations
>
> 1. Most reviewed systems assume dense in field sensor coverage. Smallholder plots in India rarely have this, which is why our design leans on forecast and satellite derived inputs with sensors treated as optional enrichment.
> 2. Evaluation is usually reported over a single cropping season at a single site. Generalisation across soil types is asserted more often than it is demonstrated.
> 3. Cloud cost and latency are almost never reported, even in papers that propose a cloud deployment. Our Azure services planning table addresses this directly.
> 4. Farmer facing delivery of the recommendation is treated as an afterthought. The notification layer in our architecture is a deliberate response to this.
>
> \## Carried into the project
>
> The consolidated research gap in the main document draws points 1 and 3 from this list. Points 2 and 4 informed the objectives on multi soil validation and on notification delivery.
>
> Status: Phase-I. To be extended with per paper annotations during Phase-II.
