/**
 * Plugin Tab Registry
 * ====================
 *
 * Maps backend plugin tab IDs to their React component implementations.
 * This enables dynamic rendering of plugin tabs in detail pages based on
 * data from the `/tabs/{object_type}` API endpoint.
 *
 * To add a new plugin tab:
 * 1. Create the tab component in `@/components/plugins/<name>/`
 * 2. Register it here with `registerPluginTab()`
 * 3. The tab will automatically appear in user/group detail pages
 */

import type { ComponentType } from 'react'

/**
 * Props that every plugin tab component must accept.
 */
export interface PluginTabProps {
  /** The uid (for users) or cn (for groups) of the object */
  uid: string
  /** Display name of the object */
  displayName: string
}

/**
 * Metadata for a registered plugin tab component.
 */
interface PluginTabRegistration {
  /** The React component to render */
  component: ComponentType<PluginTabProps>
  /** Tab ID from the backend (e.g. 'posix', 'ssh', 'mail') */
  tabId: string
}

/**
 * Internal registry mapping tab IDs to their components.
 */
const registry = new Map<string, PluginTabRegistration>()

/**
 * Register a plugin tab component.
 *
 * @param tabId - The backend tab ID (must match `TabDefinition.id`)
 * @param component - The React component to render for this tab
 */
export function registerPluginTab(
  tabId: string,
  component: ComponentType<PluginTabProps>,
): void {
  registry.set(tabId, { tabId, component })
}

/**
 * Get the React component for a given tab ID.
 * Returns undefined if no component is registered for this tab.
 */
export function getPluginTabComponent(
  tabId: string,
): ComponentType<PluginTabProps> | undefined {
  return registry.get(tabId)?.component
}

/**
 * Check if a plugin tab has a registered component.
 */
export function hasPluginTab(tabId: string): boolean {
  return registry.has(tabId)
}

/**
 * Get all registered tab IDs.
 */
export function getRegisteredTabIds(): string[] {
  return Array.from(registry.keys())
}
