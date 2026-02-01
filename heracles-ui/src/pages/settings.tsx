import { useState } from "react";
import { PageHeader, LoadingPage, ErrorDisplay } from "@/components/common";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  CategorySettingsPanel,
  PluginsTabContent,
  ConfigHistoryPanel,
} from "@/components/settings";
import { useConfig } from "@/hooks/use-config";
import {
  Settings,
  Puzzle,
  History,
  Shield,
  Database,
  KeyRound,
  Clock,
  FileText,
  Camera,
  Cog,
} from "lucide-react";

// Icon mapping for categories
const categoryIcons: Record<string, React.ElementType> = {
  general: Cog,
  ldap: Database,
  security: Shield,
  password: KeyRound,
  session: Clock,
  audit: FileText,
  snapshots: Camera,
};

export function SettingsPage() {
  const { data, isLoading, error } = useConfig();
  const [activeTab, setActiveTab] = useState("general");

  if (isLoading) {
    return <LoadingPage message="Loading configuration..." />;
  }

  if (error) {
    return (
      <ErrorDisplay
        message={error.message || "Failed to load configuration"}
      />
    );
  }

  if (!data) {
    return (
      <ErrorDisplay message="No configuration data available" />
    );
  }

  const { categories, plugins } = data;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <PageHeader
        title="Settings"
        description="Configure your Heracles instance and manage plugins"
      />

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex-1 flex flex-col min-h-0"
      >
        <div className="border-b px-4 shrink-0">
          <TabsList className="h-auto p-1 bg-transparent gap-1 flex-wrap justify-start">
            {/* Category tabs */}
            {categories.map((category) => {
              const Icon = categoryIcons[category.name] || Settings;
              return (
                <TabsTrigger
                  key={category.name}
                  value={category.name}
                  className="data-[state=active]:bg-muted gap-2"
                >
                  <Icon className="h-4 w-4" />
                  {category.label}
                </TabsTrigger>
              );
            })}

            {/* Plugins tab */}
            <TabsTrigger
              value="plugins"
              className="data-[state=active]:bg-muted gap-2"
            >
              <Puzzle className="h-4 w-4" />
              Plugins
            </TabsTrigger>

            {/* History tab */}
            <TabsTrigger
              value="history"
              className="data-[state=active]:bg-muted gap-2"
            >
              <History className="h-4 w-4" />
              History
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 p-6">
          {/* Category content */}
          {categories.map((category) => (
            <TabsContent key={category.name} value={category.name} className="mt-0 h-full">
              <div className="max-w-3xl">
                <CategorySettingsPanel category={category} />
              </div>
            </TabsContent>
          ))}

          {/* Plugins content */}
          <TabsContent value="plugins" className="mt-0 h-full">
            <PluginsTabContent plugins={plugins} />
          </TabsContent>

          {/* History content */}
          <TabsContent value="history" className="mt-0 h-full">
            <div className="max-w-4xl">
              <ConfigHistoryPanel />
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

