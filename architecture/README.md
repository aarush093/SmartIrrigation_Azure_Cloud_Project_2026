# Architecture

Architecture design for *Cloud-Based Smart Irrigation Recommendation using Weather
Intelligence* (BITE412L, Dr. Priya V).

Two architecture diagrams are mandatory under the Phase-I guidelines. Both are
maintained here in three forms: renderable Mermaid source inside the markdown, an
exported PNG for the report and presentation, and an editable draw.io source.

---

## Contents

| File | Description | Status |
|---|---|---|
| `README.md` | This file | Complete |
| [`azure_cloud_architecture.md`](azure_cloud_architecture.md) | **Diagram 1** — how the Azure services interact | Complete |
| [`system_architecture.md`](system_architecture.md) | **Diagram 2** — the overall project workflow | Complete |
| `azure_cloud_architecture.png` | Exported image of Diagram 1 for the report | To be added |
| `azure_cloud_architecture.drawio` | Editable source for Diagram 1 | To be added |
| `system_architecture.png` | Exported image of Diagram 2 for the report | To be added |
| `system_architecture.drawio` | Editable source for Diagram 2 | To be added |

---

## Diagram 1 — Azure Cloud Architecture

Shows the interaction between Azure services. Per the Phase-I guidelines it
explicitly covers six elements:

| Required element | Where it is shown |
|---|---|
| **Data flow** | External sources → Data Factory → raw zone → feature computation → field state → recommendation engine → Service Bus → notification → clients, plus the return path from farmer action |
| **Storage** | Blob Storage, Cosmos DB, SQL Database, Azure Backup |
| **Processing** | Data Factory, three Azure Functions, Service Bus, Redis cache, Azure ML training and inference |
| **Authentication** | Microsoft Entra ID, API Management, Key Vault, Front Door with WAF, VNet private endpoints |
| **Notifications** | Azure Notification Hubs (push), Azure Communication Services (SMS) |
| **Monitoring** | Application Insights, Azure Monitor with five configured alert rules |

---

## Diagram 2 — Complete System Architecture

Shows the end-to-end project workflow across seven stages: data acquisition →
cloud ingestion and storage → intelligence layer → recommendation → delivery →
farmer action → feedback and learning.

The two feedback paths are drawn deliberately as the distinguishing feature: the
logged applied volume corrects the field water balance immediately, while
accumulated outcomes drive scheduled model retraining.

---

## Design principle behind both diagrams

**Weather forecast data is the primary signal, not a refinement.** In the surveyed
literature, forecast data is typically layered over sensor-driven control as an
optional enhancement. Here the causality is inverted: forecast evaporative demand
and predicted rainfall drive the decision, and field observation corrects it. This
is what allows the system to withhold irrigation ahead of rain — the highest-value
decision it makes, and one that fixed-interval and threshold systems structurally
cannot take.

A direct consequence is that **soil moisture sensors are optional**. In Diagram 2
the IoT sensor input is drawn as a dashed line; the arrow can be removed and the
system still functions.

---

## Rendering the diagrams

The Mermaid source inside each markdown file renders directly on GitHub. To export
an image without draw.io, paste the Mermaid block into <https://mermaid.live> and
use its PNG export.

For the report and presentation, the draw.io versions using the official Azure
icon set (draw.io → *More Shapes* → *Networking* → *Azure*) are preferred, exported
at 300% zoom with a 10 px border and a white background.

---

*Phase-I: planning and documentation. Diagrams describe the proposed design;
implementation begins in Phase-II.*
