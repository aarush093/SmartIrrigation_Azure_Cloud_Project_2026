# Azure Infrastructure

**Owner:** Aarush Pandit (23BIT0416)
**Branch:** `feature/student2`
**Status:** Phase-I — no code. Implementation begins in Phase-II.

---

## Purpose

Infrastructure as code for every Azure resource the project uses.

**The rule that governs this folder: if a resource is not defined here, it does not
exist.** No resource is created by hand in the Azure Portal. This is what makes the
architecture reproducible by an examiner and not only by the team.

---

## What will be built here (Phase-II)

| File group | Contents |
|---|---|
| **Bicep modules** | One module per service group — storage, database, compute, ML, networking, security, notifications, monitoring |
| **Main template** | Composes the modules, wires managed identities and role assignments, outputs connection endpoints |
| **Parameter files** | Environment-specific values for dev and production. **No secrets** — only resource names, SKUs and regions |
| **Data Factory pipelines** | Pipeline and dataset definitions for the daily ingestion of forecast, reanalysis and soil data |
| **Deployment scripts** | `az deployment group create` wrappers and a teardown script for cost control |

---

## Planned structure

```
azure/
├── README.md
├── main.bicep
├── main.parameters.dev.json
├── main.parameters.prod.json
├── modules/
│   ├── storage.bicep          # Blob Storage with lifecycle rules
│   ├── cosmos.bicep           # Cosmos DB account and containers
│   ├── sql.bicep              # SQL Database and firewall
│   ├── redis.bicep            # Cache for Redis
│   ├── functions.bicep        # Function App, consumption plan, managed identity
│   ├── servicebus.bicep       # Queue with dead-letter configuration
│   ├── machinelearning.bicep  # ML workspace, Container Registry, endpoint
│   ├── apim.bicep             # API Management
│   ├── identity.bicep         # Entra ID app registrations and role assignments
│   ├── keyvault.bicep         # Key Vault with access policies
│   ├── network.bicep          # VNet, subnets, private endpoints
│   ├── frontdoor.bicep        # Front Door with WAF policy
│   ├── notifications.bicep    # Notification Hubs and Communication Services
│   ├── staticwebapp.bicep     # Static Web Apps
│   └── monitoring.bicep       # Application Insights, Azure Monitor alert rules
├── datafactory/
│   ├── pipeline_daily_ingest.json
│   ├── dataset_openmeteo.json
│   ├── dataset_nasapower.json
│   └── dataset_soilgrids.json
└── scripts/
    ├── deploy.sh
    ├── teardown.sh
    └── seed_reference_data.sql
```

---

## Resource inventory

| Layer | Resources |
|---|---|
| **Ingestion and processing** | Data Factory, Function App (consumption plan), Service Bus namespace and queue, Cache for Redis |
| **Storage** | Storage Account with Blob containers (`raw`, `features`, `models`), Cosmos DB account with containers (`field-state`, `recommendations`), SQL Database, Backup vault |
| **Machine learning** | ML workspace, Container Registry, managed online endpoint |
| **Authentication and API** | Entra ID app registrations, API Management instance, Key Vault |
| **Notifications** | Notification Hub namespace, Communication Services resource |
| **Networking and security** | Virtual Network with subnets, private endpoints for Cosmos DB / SQL / Blob / Key Vault, Front Door profile with WAF policy |
| **Presentation** | Static Web App, App Service plan (reserved for later scale-up) |
| **Monitoring** | Log Analytics workspace, Application Insights, five Azure Monitor alert rules |

---

## The five alert rules (Objective 5 acceptance evidence)

| # | Alert | Trigger condition |
|---|---|---|
| 1 | Ingestion failure | Data Factory pipeline failure, or any registered field holding forecast data older than 24 hours |
| 2 | Model endpoint error rate | ML endpoint HTTP 5xx rate above threshold over a 15-minute window |
| 3 | Notification failure | Service Bus dead-letter queue depth above zero |
| 4 | Cost threshold | Resource group spend exceeding the monthly budget forecast |
| 5 | Authentication anomaly | Elevated failed sign-in rate through Entra ID |

---

## Security posture

| Control | Implementation |
|---|---|
| **No secrets in code** | All credentials in Key Vault; Functions authenticate via system-assigned managed identity; CI runs automated secret scanning |
| **Private data plane** | Cosmos DB, SQL Database, Blob Storage and Key Vault reachable only through private endpoints inside the VNet |
| **Least privilege** | Each managed identity receives only the RBAC roles its component requires, assigned in Bicep and reviewable in the repository |
| **Public edge protection** | Front Door with WAF in front of the dashboard and API surface, covering SQL injection, cross-site scripting and volumetric abuse |
| **Tenant isolation** | Entra ID role-based access enforced at API Management, so a farmer can retrieve only their own fields |

---

## Cost control

This is a student project on a limited subscription, so cost is an engineering
constraint, not an afterthought.

| Measure | Effect |
|---|---|
| Functions on the consumption plan | A field costs nothing on days it is not processed |
| Redis cache keyed by weather grid cell | Many fields per district cost one upstream API call, keeping the platform inside Open-Meteo's free tier |
| Blob lifecycle rules | Ageing raw forecast archives move to Cool then Archive tiers |
| Cosmos DB serverless or minimum throughput in development | Avoids provisioned-throughput charges during build |
| `teardown.sh` | Removes the entire resource group when not actively developing |
| Cost threshold alert | Budget breach is surfaced before it becomes a problem |

---

## Deployment sequence (Phase-II)

```bash
# 1. Log in and set the subscription
az login
az account set --subscription "<subscription-id>"

# 2. Create the resource group
az group create --name rg-smartirrigation-dev --location centralindia

# 3. Deploy the infrastructure
az deployment group create \
  --resource-group rg-smartirrigation-dev \
  --template-file main.bicep \
  --parameters @main.parameters.dev.json

# 4. Seed reference data (crops, coefficients, growth stages)
./scripts/seed_reference_data.sql

# 5. Deploy Data Factory pipelines
# 6. Deploy Function code
# 7. Deploy the frontend to Static Web Apps
```

---

*Phase-I: planning and documentation. No Azure resources have been provisioned.*
