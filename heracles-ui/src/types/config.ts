/**
 * Configuration Types
 * ===================
 *
 * TypeScript types for the Heracles configuration system.
 */

// Field type enum matching backend ConfigFieldType
export type ConfigFieldType =
  | "string"
  | "integer"
  | "boolean"
  | "float"
  | "list"
  | "select"
  | "multiselect"
  | "password"
  | "path"
  | "url"
  | "email"
  | "json";

// Option for select/multiselect fields
export interface ConfigFieldOption {
  value: string | number | boolean;
  label: string;
}

// Validation rules for a config field
export interface ConfigFieldValidation {
  minLength?: number;
  maxLength?: number;
  minValue?: number;
  maxValue?: number;
  pattern?: string;
  patternError?: string;
}

// Single configuration field definition
export interface ConfigField {
  key: string;
  label: string;
  description?: string;
  fieldType: ConfigFieldType;
  defaultValue: unknown;
  required?: boolean;
  sensitive?: boolean;
  requiresRestart?: boolean;
  validation?: ConfigFieldValidation;
  options?: ConfigFieldOption[];
}

// Section of configuration fields
export interface ConfigSection {
  id: string;
  label: string;
  description?: string;
  fields: ConfigField[];
}

// Category of configuration settings
export interface ConfigCategory {
  name: string;
  label: string;
  description?: string;
  icon?: string;
  displayOrder: number;
  settings: ConfigSetting[];
}

// Single configuration setting with current value
export interface ConfigSetting {
  key: string;
  value: unknown;
  defaultValue: unknown;
  fieldType: ConfigFieldType;  // API returns fieldType (camelCase alias)
  label?: string;
  description?: string;
  validation?: ConfigFieldValidation;  // API returns validation, not validationRules
  options?: ConfigFieldOption[];
  requiresRestart?: boolean;
  sensitive?: boolean;
  dependsOn?: string;
  dependsOnValue?: unknown;
}

// Plugin configuration
export interface PluginConfig {
  name: string;
  description?: string;
  version: string;
  enabled: boolean;
  sections: ConfigSection[];
  config: Record<string, unknown>;
  updatedAt?: string;
  updatedBy?: string;
  // Computed properties for display
  priority?: number;  // For sorting, defaults to 50 if not set
}

// Configuration history entry
export interface ConfigHistoryEntry {
  id: string;
  category?: string;
  pluginName?: string;
  settingKey?: string;
  oldValue?: unknown;
  newValue: unknown;
  changedBy: string;
  changedAt: string;
  reason?: string;
}

// API Response types

// Full configuration response
export interface GlobalConfigResponse {
  categories: ConfigCategory[];
  plugins: PluginConfig[];
}

// Category list response
export interface ConfigCategoriesResponse {
  categories: ConfigCategory[];
}

// Single setting update request
export interface ConfigUpdateRequest {
  value: unknown;
  reason?: string;
}

// Bulk settings update request
export interface ConfigBulkUpdateRequest {
  settings: {
    category: string;
    key: string;
    value: unknown;
  }[];
  reason?: string;
}

// Plugin config update request
export interface PluginConfigUpdateRequest {
  config: Record<string, unknown>;
  reason?: string;
}

// History query params
export interface ConfigHistoryParams {
  entityType?: "setting" | "plugin";
  entityId?: string;
  limit?: number;
  offset?: number;
}

// History response
export interface ConfigHistoryResponse {
  items: ConfigHistoryEntry[];
  total: number;
  page: number;
  pageSize: number;
}

// Validation error
export interface ConfigValidationError {
  field: string;
  message: string;
}

// Config update result
export interface ConfigUpdateResult {
  success: boolean;
  requiresRestart?: boolean;
  errors?: ConfigValidationError[];
}

// Settings form state (for UI)
export interface SettingsFormState {
  values: Record<string, unknown>;
  errors: Record<string, string>;
  isDirty: boolean;
  isSubmitting: boolean;
}

// Plugin settings form state
export interface PluginSettingsFormState extends SettingsFormState {
  pluginName: string;
  enabled: boolean;
}
