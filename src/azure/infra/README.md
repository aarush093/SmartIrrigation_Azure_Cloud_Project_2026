# Infrastructure as code

Bicep for every Azure resource this project uses. **If a resource is not defined
here, it does not exist**: nothing is created by hand in the portal, which is
what makes the architecture reproducible by an examiner and not only by the
team.

## Nothing here has been deployed

`make deploy-plan` runs `az deployment group what-if` and nothing else.
`make deploy` exists but is for the repository owner to run after `az login` on
his own subscription. No credit has been spent.

## Everything is on a free or consumption tier

The tier is stated in a comment on every resource. This has to run on an Azure
for Students subscription, and demonstrating that it can is part of the point.

| Resource | Tier | Why that tier |
|---|---|---|
| Storage | Standard_LRS | Every blob is either reproducible from a public API or a cached artefact, so the cheapest redundancy is correct |
| Cosmos DB | Serverless | Per-farmer cost is a handful of documents a day; a provisioned floor would dominate the bill |
| Functions | Y1 Consumption | No charge when idle. The cold-start question is settled in the feasibility note |
| Key Vault | Standard | The only tier without an HSM charge |
| Log Analytics | PerGB2018, capped at 0.1 GB/day | A hard cap, so a runaway log loop cannot spend the credit |
| AI Speech | F0 | Free. The blob cache means each distinct script is synthesised once |
| AI Document Intelligence | F0 | Free, 500 pages a month. Circulars are parsed once when published |
| AI Translator | F0 | Free. Used only to draft masters, which a native speaker then checks |
| Static Web Apps | Free | 100 GB a month, which a three-tile page will not approach |
| API Management | Consumption | Pay per call, no instance charge, scales to zero |
| Machine Learning | Basic, **no compute** | Registration and versioning only; training runs locally |
| Communication Services | Standard, **no phone number** | See below |

## The Communication Services resource has no phone number

And none can be attached. India is not in the country and region list for
Communication Services telephone numbers, and numbers cannot be acquired on
trial accounts or with Azure free credits in any case.
`docs/ACS_MISSED_CALL_FEASIBILITY.md` section 5 has the detail.

The resource is deployed anyway, because the Event Grid system topic and the
webhook subscription hang off it and they are the evidence that the integration
is real. The demonstration runs on the simulated telephony console.

## Two deliberate departures from Microsoft's default advice

**Event Grid retry is generous, not aggressive.** Microsoft recommends two
delivery attempts and a one-minute time to live for `IncomingCall`, because in
an answer-the-call design a late event is useless. This design never answers, so
a late event is still a valid field observation and may be the only one that
field produces that day. The subscription uses a 12-hour TTL, 30 attempts, and a
dead-letter container in Blob Storage.

**Cosmos DB has local authentication disabled.** Objective 5 requires
data-plane services behind private endpoints or authenticated gateways. Virtual
Network and private endpoints are deferred to Phase-III on cost grounds, so the
requirement is met through authenticated gateways instead: managed identity with
key access switched off, Key Vault with RBAC, and API Management in front of the
operator endpoints.

## Deploying

```bash
az login
az group create --name rg-smartirr-dev --location centralindia
export AZURE_RESOURCE_GROUP=rg-smartirr-dev

make deploy-plan     # what-if only, changes nothing
make deploy          # owner runs this, not the build
```

After the first deployment, add the three secrets by hand. They are never in
source control and never in a parameter file:

```bash
az keyvault secret set --vault-name kv-smartirr-dev --name speech-key --value '...'
az keyvault secret set --vault-name kv-smartirr-dev --name docint-key --value '...'
az keyvault secret set --vault-name kv-smartirr-dev --name acs-connection-string --value '...'
```
