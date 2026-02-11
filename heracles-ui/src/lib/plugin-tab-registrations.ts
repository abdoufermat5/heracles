/**
 * Plugin Tab Registrations
 * =========================
 *
 * Registers all known plugin tab components with the plugin tab registry.
 * Import this file once at app startup (e.g. in main.tsx or App.tsx).
 *
 * When adding a new plugin with a user/group tab, add the registration here.
 */

import { registerPluginTab } from '@/lib/plugin-tab-registry'
import { PosixUserTab } from '@/components/plugins/posix'
import { SSHUserTab } from '@/components/plugins/ssh'
import { MailUserTab } from '@/components/plugins/mail'

// User tabs
registerPluginTab('posix', PosixUserTab)
registerPluginTab('ssh', SSHUserTab)
registerPluginTab('mail', MailUserTab)

// Group tabs could be registered here too:
// registerPluginTab('posix-group', PosixGroupTab)
// registerPluginTab('mail-group', MailGroupTab)
