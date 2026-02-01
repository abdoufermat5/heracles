/**
 * Plugins Tab Content
 * ===================
 *
 * A split-pane layout with vertical plugin navigation on the left
 * and plugin settings on the right.
 */

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { PluginSettingsPanel } from "./plugin-settings-panel";
import type { PluginConfig } from "@/types/config";
import { Puzzle, ChevronRight } from "lucide-react";

interface PluginsTabContentProps {
  plugins: PluginConfig[];
}

export function PluginsTabContent({ plugins }: PluginsTabContentProps) {
  const sortedPlugins = [...plugins].sort((a, b) => a.name.localeCompare(b.name));
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(
    sortedPlugins.length > 0 ? sortedPlugins[0].name : null
  );

  const currentPlugin = sortedPlugins.find((p) => p.name === selectedPlugin);

  if (plugins.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center py-12 text-muted-foreground">
          <Puzzle className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No plugins installed</p>
          <p className="text-sm">Plugins extend Heracles with additional features</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full gap-6">
      {/* Left sidebar - Plugin list */}
      <div className="w-64 shrink-0 border rounded-lg bg-card flex flex-col">
        <div className="p-3 border-b shrink-0">
          <h3 className="font-medium text-sm text-muted-foreground">
            Installed Plugins ({plugins.length})
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sortedPlugins.map((plugin) => (
            <button
              key={plugin.name}
              onClick={() => setSelectedPlugin(plugin.name)}
              className={cn(
                "w-full flex items-center justify-between px-3 py-2 rounded-md text-left transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                selectedPlugin === plugin.name
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground"
              )}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Puzzle className="h-4 w-4 shrink-0" />
                <span className="truncate text-sm font-medium capitalize">
                  {plugin.name}
                </span>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Badge
                  variant={plugin.enabled ? "default" : "secondary"}
                  className="text-xs px-1.5 py-0"
                >
                  {plugin.enabled ? "On" : "Off"}
                </Badge>
                {selectedPlugin === plugin.name && (
                  <ChevronRight className="h-4 w-4" />
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right content - Plugin settings */}
      <div className="flex-1 min-w-0 overflow-y-auto">
        {currentPlugin ? (
          <PluginSettingsPanel
            key={currentPlugin.name}
            plugin={currentPlugin}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            Select a plugin to configure
          </div>
        )}
      </div>
    </div>
  );
}
