import openapi from '../../api/generated/openapi.json'

// Read from the backend's own OpenAPI document, so this panel moves with the contract.
const schemas = openapi.components.schemas
const alerts = schemas.IncidentCase.properties.alerts

export const caseContract = {
  caseFields: schemas.IncidentCase.required,
  alertFields: schemas.Alert.required,
  sources: schemas.Alert.properties.source_system.enum,
  minAlerts: alerts.minItems,
  maxAlerts: alerts.maxItems,
}
