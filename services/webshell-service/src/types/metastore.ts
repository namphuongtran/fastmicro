/**
 * Metastore Types
 *
 * Type definitions for feature flags and configuration metadata.
 * These types mirror the backend metastore-service API models.
 */

// ============================================================================
// Enums
// ============================================================================

/**
 * Deployment environments
 */
export const Environment = {
  DEVELOPMENT: "development",
  STAGING: "staging",
  PRODUCTION: "production",
  TEST: "test",
} as const;

export type Environment = (typeof Environment)[keyof typeof Environment];

/**
 * Operators for targeting rules
 */
export const Operator = {
  EQUALS: "eq",
  NOT_EQUALS: "neq",
  CONTAINS: "contains",
  NOT_CONTAINS: "not_contains",
  STARTS_WITH: "starts_with",
  ENDS_WITH: "ends_with",
  REGEX: "regex",
  IN: "in",
  NOT_IN: "not_in",
  GREATER_THAN: "gt",
  LESS_THAN: "lt",
  GREATER_THAN_OR_EQUAL: "gte",
  LESS_THAN_OR_EQUAL: "lte",
} as const;

export type Operator = (typeof Operator)[keyof typeof Operator];

/**
 * Content types for metadata values
 */
export const ContentType = {
  JSON: "application/json",
  YAML: "application/yaml",
  TEXT: "text/plain",
  BINARY: "application/octet-stream",
  XML: "application/xml",
  PROPERTIES: "text/x-java-properties",
} as const;

export type ContentType = (typeof ContentType)[keyof typeof ContentType];

// ============================================================================
// Feature Flag Types
// ============================================================================

/**
 * Targeting rule for feature flag evaluation
 */
export interface TargetingRule {
  id: string;
  feature_flag_id: string;
  priority: number;
  attribute: string;
  operator: Operator;
  value: string;
  result: boolean | string | number | Record<string, unknown>;
  description: string | null;
}

/**
 * Feature flag entity
 */
export interface FeatureFlag {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  default_value: boolean | string | number | Record<string, unknown>;
  rollout_percentage: number;
  targeting_rules: TargetingRule[];
  tenant_overrides: Record<string, unknown>;
  environment_overrides: Record<Environment, unknown>;
  expires_at: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

/**
 * Request to create a feature flag
 */
export interface CreateFeatureFlagRequest {
  name: string;
  description?: string;
  enabled?: boolean;
  default_value?: boolean | string | number | Record<string, unknown>;
  rollout_percentage?: number;
  tags?: string[];
  expires_at?: string;
}

/**
 * Request to update a feature flag
 */
export interface UpdateFeatureFlagRequest {
  description?: string;
  enabled?: boolean;
  default_value?: boolean | string | number | Record<string, unknown>;
  rollout_percentage?: number;
  tags?: string[];
  expires_at?: string | null;
}

/**
 * Request to add a targeting rule
 */
export interface AddTargetingRuleRequest {
  priority: number;
  attribute: string;
  operator: Operator;
  value: string;
  result: boolean | string | number | Record<string, unknown>;
  description?: string;
}

/**
 * Request to evaluate a feature flag
 */
export interface EvaluateFeatureFlagRequest {
  context: Record<string, unknown>;
  environment?: Environment;
  tenant_id?: string;
}

/**
 * Response from feature flag evaluation
 */
export interface EvaluateFeatureFlagResponse {
  flag_name: string;
  enabled: boolean;
  value: boolean | string | number | Record<string, unknown>;
  reason: string;
  rule_id: string | null;
}

/**
 * Paginated response for feature flags
 */
export interface PaginatedFeatureFlags {
  items: FeatureFlag[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================================================
// Metadata Types
// ============================================================================

/**
 * Metadata entry
 */
export interface MetadataEntry {
  id: string;
  key: string;
  value: unknown;
  version: number;
  created_at: string;
  updated_at: string;
}

/**
 * Request to create metadata
 */
export interface CreateMetadataRequest {
  key: string;
  value: unknown;
}

/**
 * Request to update metadata
 */
export interface UpdateMetadataRequest {
  value: unknown;
}

/**
 * Paginated response for metadata
 */
export interface PaginatedMetadata {
  items: MetadataEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * Configuration entry with versioning
 */
export interface ConfigurationEntry {
  id: string;
  key: string;
  value: unknown;
  content_type: ContentType;
  environment: Environment;
  tenant_id: string | null;
  version: number;
  is_encrypted: boolean;
  description: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

/**
 * Request to create configuration
 */
export interface CreateConfigurationRequest {
  key: string;
  value: unknown;
  content_type?: ContentType;
  environment?: Environment;
  tenant_id?: string;
  is_encrypted?: boolean;
  description?: string;
  tags?: string[];
}

/**
 * Request to update configuration
 */
export interface UpdateConfigurationRequest {
  value: unknown;
  description?: string;
  tags?: string[];
}

// ============================================================================
// Query Parameters
// ============================================================================

/**
 * Query parameters for listing feature flags
 */
export interface FeatureFlagQueryParams {
  page?: number;
  page_size?: number;
  enabled?: boolean;
  tags?: string[];
  search?: string;
  environment?: Environment;
}

/**
 * Query parameters for listing metadata
 */
export interface MetadataQueryParams {
  page?: number;
  page_size?: number;
  prefix?: string;
  search?: string;
}

/**
 * Query parameters for listing configurations
 */
export interface ConfigurationQueryParams {
  page?: number;
  page_size?: number;
  environment?: Environment;
  tenant_id?: string;
  prefix?: string;
  tags?: string[];
}

// ============================================================================
// UI State Types
// ============================================================================

/**
 * Feature flag form data for create/edit
 */
export interface FeatureFlagFormData {
  name: string;
  description: string;
  enabled: boolean;
  defaultValue: string;
  defaultValueType: "boolean" | "string" | "number" | "json";
  rolloutPercentage: number;
  tags: string[];
  expiresAt: string | null;
}

/**
 * Targeting rule form data
 */
export interface TargetingRuleFormData {
  attribute: string;
  operator: Operator;
  value: string;
  resultType: "boolean" | "string" | "number" | "json";
  result: string;
  description: string;
}

/**
 * Feature flag table column
 */
export interface FeatureFlagColumn {
  id: keyof FeatureFlag | "actions";
  label: string;
  sortable: boolean;
  width?: string;
}
