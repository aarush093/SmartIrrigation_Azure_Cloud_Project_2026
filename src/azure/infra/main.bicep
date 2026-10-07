// Smart Irrigation, Phase-II infrastructure.
//
// Every resource here is on a free or consumption tier, and the tier is stated
// in a comment on each one. This runs on an Azure for Students subscription and
// the whole point of the exercise is that it can.
//
// NOT deployed by anyone but the repository owner. `make deploy-plan` runs
// `az deployment group what-if` and nothing else.
//
// One resource is deliberately incomplete: the Communication Services resource
// carries NO PHONE NUMBER. India is not in the country list for Communication
// Services telephone numbers, and numbers cannot be acquired on trial accounts
// or with free credits in any case. See docs/ACS_MISSED_CALL_FEASIBILITY.md
// section 5. The resource is deployed to show the integration is real; the
// demonstration runs on the simulated telephony console.

targetScope = 'resourceGroup'

@description('Environment name. Used as a suffix on every resource name.')
@allowed(['dev', 'pilot'])
param environment string = 'dev'

@description('Location for all resources. Central India is closest to the pilot districts.')
param location string = resourceGroup().location

@description('Short project prefix. Azure name length limits are tight, so keep it short.')
@minLength(3)
@maxLength(8)
param prefix string = 'smartirr'

@description('Toggle Azure Communication Services. Off by default: it is deployed to show the integration, and no phone number can be attached on this subscription.')
param deployCommunicationServices bool = true

@description('Toggle the Machine Learning workspace. It has no compute and exists for model registration only.')
param deployMachineLearning bool = true

var suffix = '${prefix}-${environment}'
var storageName = toLower(replace('${prefix}${environment}st', '-', ''))
var tags = {
  project: 'Cloud-Based Smart Irrigation Recommendation'
  course: 'BITE412L'
  phase: 'Phase-II'
  environment: environment
}

// ---------------------------------------------------------------------------
// Storage. Standard_LRS is the cheapest redundancy and is correct here: every
// blob is either reproducible from a public API or a cached artefact.
// ---------------------------------------------------------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

// raw           forecast and soil responses as fetched, for reproducibility
// discom-pdfs   circulars fed to Document Intelligence. Never committed to git.
// tts-cache     synthesised audio keyed by script hash; the same script recurs
//               daily, so each utterance is synthesised once for the pilot
// deadletter    Event Grid dead-letter destination. See the subscription below:
//               a missed call that fails delivery must be preserved, not lost
var containers = ['raw', 'discom-pdfs', 'tts-cache', 'deadletter']
resource blobContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [
  for name in containers: {
    parent: blobService
    name: name
    properties: { publicAccess: 'None' }
  }
]

// ---------------------------------------------------------------------------
// Cosmos DB. Serverless: per-farmer cost is a handful of documents a day, and a
// provisioned throughput floor would dominate the bill at pilot scale.
// ---------------------------------------------------------------------------
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: 'cosmos-${suffix}'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    // Serverless, so there is no minimum throughput charge.
    capabilities: [ { name: 'EnableServerless' } ]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [ { locationName: location, failoverPriority: 0, isZoneRedundant: false } ]
    // Objective 5: no key-based access. The Functions identity uses RBAC.
    disableLocalAuth: true
    minimalTlsVersion: 'Tls12'
    backupPolicy: {
      // Continuous backup replaces the separately declared Backup vault from
      // Phase-I. See docs/AZURE_SERVICES_PHASE2.md.
      type: 'Continuous'
      continuousModeProperties: { tier: 'Continuous7Days' }
    }
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'irrigation'
  properties: { resource: { id: 'irrigation' } }
}

// Partition keys are chosen for the read pattern the daily loop actually has.
// Everything is read per farmer or per field once a day, so those are the keys.
var cosmosContainers = [
  { name: 'farmers', key: '/farmer_id' }
  { name: 'fields', key: '/farmer_id' }
  { name: 'feeder_windows', key: '/feeder_id' }
  { name: 'schedules', key: '/field_id' }
  // Partitioned by farmer, with the deduplication key as the document id, so
  // the uniqueness constraint that makes replayed events a no-op is enforced by
  // the database rather than by application memory.
  { name: 'events', key: '/farmer_id' }
]

resource containers_ 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = [
  for c in cosmosContainers: {
    parent: cosmosDatabase
    name: c.name
    properties: {
      resource: {
        id: c.name
        partitionKey: { paths: [ c.key ], kind: 'Hash' }
      }
    }
  }
]

// ---------------------------------------------------------------------------
// Observability. Both within the free allowance at pilot scale.
// ---------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${suffix}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: {
      // Hard cap. A runaway log loop must not spend the student credit.
      dailyQuotaGb: json('0.1')
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${suffix}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ---------------------------------------------------------------------------
// Key Vault. RBAC rather than access policies, so the Functions identity is
// granted a role rather than an entry in a list.
// ---------------------------------------------------------------------------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${suffix}'
  location: location
  tags: tags
  properties: {
    // Standard is the only tier without an HSM charge.
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

// ---------------------------------------------------------------------------
// Functions on consumption. The hosting decision, and why Microsoft's
// cold-start warning does not bind here, is in
// docs/ACS_MISSED_CALL_FEASIBILITY.md Decision 1: this app never answers a
// call, so a missed rejection means the call rings out and the event still
// arrives.
// ---------------------------------------------------------------------------
resource hostingPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'plan-${suffix}'
  location: location
  tags: tags
  // Y1 Dynamic is the consumption plan: no charge when idle.
  sku: { name: 'Y1', tier: 'Dynamic' }
  properties: { reserved: true }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: 'func-${suffix}'
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'AzureWebJobsStorage__accountName', value: storage.name }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
        { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
        { name: 'COSMOS_DATABASE', value: 'irrigation' }
        { name: 'SPEECH_REGION', value: location }
        { name: 'SPEECH_BLOB_BASE_URL', value: '${storage.properties.primaryEndpoints.blob}tts-cache' }
        // Secrets are referenced, never valued. The Functions identity reads
        // them from Key Vault at runtime.
        { name: 'SPEECH_KEY', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=speech-key)' }
        { name: 'ACS_CONNECTION_STRING', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=acs-connection-string)' }
        { name: 'DOCINT_KEY', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=docint-key)' }
        // Feature flags. ACS is off because no number can be provisioned on
        // this subscription; Speech is on because F0 needs no number.
        { name: 'ACS_ENABLED', value: 'false' }
        { name: 'SPEECH_ENABLED', value: 'true' }
        { name: 'MISSEDCALL_NUMBER_WATER_GIVEN', value: '' }
        { name: 'MISSEDCALL_NUMBER_POWER_FAILED', value: '' }
        { name: 'MISSEDCALL_NUMBER_REPEAT', value: '' }
      ]
    }
  }
}

// ---------------------------------------------------------------------------
// Role assignments. Managed identity throughout; no connection string anywhere
// in configuration that a person could read.
// ---------------------------------------------------------------------------
var keyVaultSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'
var storageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var cosmosDataContributor = '00000000-0000-0000-0000-000000000002'

resource kvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, functionApp.id, keyVaultSecretsUser)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUser)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource blobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, functionApp.id, storageBlobDataContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource cosmosRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, functionApp.id, cosmosDataContributor)
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributor}'
    principalId: functionApp.identity.principalId
    scope: cosmos.id
  }
}

// ---------------------------------------------------------------------------
// Azure AI services. All on free tiers: F0 for Speech and Document
// Intelligence, F0 for Translator. Each is limited but sufficient for three
// pilot farmers, and the limits are stated in AZURE_SERVICES_PHASE2.md.
// ---------------------------------------------------------------------------
resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'speech-${suffix}'
  location: location
  tags: tags
  kind: 'SpeechServices'
  // F0: free tier. Neural TTS is capped per month, which the blob cache makes
  // sufficient because each distinct script is synthesised once.
  sku: { name: 'F0' }
  properties: { customSubDomainName: 'speech-${suffix}', publicNetworkAccess: 'Enabled' }
}

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'docint-${suffix}'
  location: location
  tags: tags
  kind: 'FormRecognizer'
  // F0: free tier, 500 pages a month. DISCOM circulars are parsed once when
  // published, so this is far more than enough.
  sku: { name: 'F0' }
  properties: { customSubDomainName: 'docint-${suffix}', publicNetworkAccess: 'Enabled' }
}

resource translator 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'trans-${suffix}'
  location: 'global'
  tags: tags
  kind: 'TextTranslation'
  // F0: free tier. Used only to draft new language masters, which are then
  // checked by a native speaker before use, so volume is negligible.
  sku: { name: 'F0' }
  properties: { customSubDomainName: 'trans-${suffix}' }
}

// ---------------------------------------------------------------------------
// Communication Services. NO PHONE NUMBER, and none can be attached: India is
// not in the supported country list and numbers cannot be acquired on trial
// accounts or with free credits. Deployed to show the integration is real.
// docs/ACS_MISSED_CALL_FEASIBILITY.md section 5.
// ---------------------------------------------------------------------------
resource communicationServices 'Microsoft.Communication/communicationServices@2023-04-01' = if (deployCommunicationServices) {
  name: 'acs-${suffix}'
  location: 'global'
  tags: tags
  properties: { dataLocation: 'India' }
}

// ---------------------------------------------------------------------------
// Static Web Apps. Free tier, pointed at the frontend once Nayan's pull request
// lands. Repository settings are supplied at deployment rather than hardcoded.
// ---------------------------------------------------------------------------
resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: 'swa-${suffix}'
  location: location
  tags: tags
  // Free tier: 100 GB bandwidth a month, which a three-tile page will not
  // approach.
  sku: { name: 'Free', tier: 'Free' }
  properties: { stagingEnvironmentPolicy: 'Enabled', allowConfigFileUpdates: true }
}

// ---------------------------------------------------------------------------
// API Management, consumption tier. Objective 5 requires data-plane services
// behind private endpoints OR authenticated gateways; this is the authenticated
// gateway, in front of the operator endpoints only. The farmer-facing channel
// is a phone call and has no endpoint to protect.
// ---------------------------------------------------------------------------
resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: 'apim-${suffix}'
  location: location
  tags: tags
  // Consumption: pay per call, no instance charge, scales to zero.
  sku: { name: 'Consumption', capacity: 0 }
  properties: {
    publisherEmail: 'aarush093@users.noreply.github.com'
    publisherName: 'Smart Irrigation, BITE412L'
  }
}

// ---------------------------------------------------------------------------
// Machine Learning workspace. NO COMPUTE PROVISIONED. It exists so the
// Objective 3 and calibration models can be registered and versioned; training
// runs locally, because a compute instance would spend the student credit while
// idle.
// ---------------------------------------------------------------------------
resource mlWorkspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = if (deployMachineLearning) {
  name: 'mlw-${suffix}'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  sku: { name: 'Basic', tier: 'Basic' }
  properties: {
    friendlyName: 'Smart Irrigation models'
    storageAccount: storage.id
    keyVault: keyVault.id
    applicationInsights: appInsights.id
  }
}

// ---------------------------------------------------------------------------
// Event Grid: inbound missed calls.
//
// The retry settings deliberately REVERSE Microsoft's guidance for
// IncomingCall. They advise two attempts and a one-minute TTL because in an
// answer-the-call design a late event is useless. Here a late event is still a
// valid field observation and may be the only one that field produces that day,
// so it is retried generously and dead-lettered rather than dropped.
// docs/ACS_MISSED_CALL_FEASIBILITY.md Decision 2.
// ---------------------------------------------------------------------------
resource acsSystemTopic 'Microsoft.EventGrid/systemTopics@2024-06-01-preview' = if (deployCommunicationServices) {
  name: 'egst-acs-${suffix}'
  location: 'global'
  tags: tags
  properties: {
    source: communicationServices.id
    topicType: 'Microsoft.Communication.CommunicationServices'
  }
}

resource incomingCallSubscription 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2024-06-01-preview' = if (deployCommunicationServices) {
  parent: acsSystemTopic
  name: 'incoming-call'
  properties: {
    destination: {
      endpointType: 'WebHook'
      properties: {
        endpointUrl: 'https://${functionApp.properties.defaultHostName}/api/acs_events'
        maxEventsPerBatch: 1
      }
    }
    filter: {
      includedEventTypes: [ 'Microsoft.Communication.IncomingCall' ]
      // Without a filter, Microsoft warns that redirect scenarios produce
      // duplicate events and "can result in infinite loops". The filter is
      // populated with the provisioned numbers at deployment; empty here
      // because none can be provisioned on this subscription.
      enableAdvancedFilteringOnArrays: true
    }
    retryPolicy: {
      // Hours, not one minute. A late reading is still a reading.
      eventTimeToLiveInMinutes: 720
      maxDeliveryAttempts: 30
    }
    deadLetterDestination: {
      endpointType: 'StorageBlob'
      properties: {
        resourceId: storage.id
        blobContainerName: 'deadletter'
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Alert rules. Five, as Objective 5 requires.
// ---------------------------------------------------------------------------
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'ag-${suffix}'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'smartirr'
    enabled: true
    emailReceivers: [
      {
        name: 'owner'
        emailAddress: 'aarush093@users.noreply.github.com'
        useCommonAlertSchema: true
      }
    ]
  }
}

// Each alert names the failure it is watching for, because an alert whose
// purpose is not obvious at 3am gets muted rather than fixed.
var alerts = [
  {
    name: 'ingest-failure'
    description: 'Weather or soil ingestion failed. Objective 1 requires 99 percent ingestion success over 30 days.'
    query: 'traces | where message has "fetch" and severityLevel >= 3'
  }
  {
    name: 'scheduler-failure'
    description: 'plan_day raised. A farmer got no decision at all today.'
    query: 'exceptions | where operation_Name has "daily_plan"'
  }
  {
    name: 'call-failure-rate'
    description: 'Outbound calls are failing. The farmer is not being reached.'
    query: 'customEvents | where name == "call_placed" and tostring(customDimensions.outcome) != "answered"'
  }
  {
    name: 'missedcall-webhook-errors'
    description: 'The acs_events webhook is erroring. Missed calls are being lost, which is the only sensor this system has.'
    query: 'requests | where name has "acs_events" and success == false'
  }
  {
    name: 'cosmos-throttling'
    description: 'Cosmos DB returned 429. Serverless throughput is being exceeded.'
    query: 'dependencies | where type has "Azure DocumentDB" and resultCode == "429"'
  }
]

resource scheduledAlerts 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = [
  for alert in alerts: {
    name: 'alert-${alert.name}-${environment}'
    location: location
    tags: tags
    properties: {
      displayName: alert.name
      description: alert.description
      severity: 2
      enabled: true
      scopes: [ appInsights.id ]
      evaluationFrequency: 'PT15M'
      windowSize: 'PT1H'
      criteria: {
        allOf: [
          {
            query: alert.query
            timeAggregation: 'Count'
            operator: 'GreaterThan'
            threshold: 0
            failingPeriods: { numberOfEvaluationPeriods: 1, minFailingPeriodsToAlert: 1 }
          }
        ]
      }
      actions: { actionGroups: [ actionGroup.id ] }
    }
  }
]

// ---------------------------------------------------------------------------
// Outputs, used by the deployment script and by local configuration.
// ---------------------------------------------------------------------------
output functionAppName string = functionApp.name
output functionAppHost string = functionApp.properties.defaultHostName
output functionPrincipalId string = functionApp.identity.principalId
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output storageAccountName string = storage.name
output keyVaultName string = keyVault.name
output staticWebAppHost string = staticWebApp.properties.defaultHostname
output appInsightsConnectionString string = appInsights.properties.ConnectionString
