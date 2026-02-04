/**
 * Plugin Settings Panel
 * =====================
 *
 * Renders settings for a single plugin configuration.
 */

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Save, RotateCcw, AlertTriangle, Database } from "lucide-react";
import { ConfigFieldComponent } from "./config-field";
import { useUpdatePluginConfig, useTogglePlugin } from "@/hooks/use-config";
import type { PluginConfig, ConfigSection, RdnChangeCheckResponse } from "@/types/config";

interface PluginSettingsPanelProps {
  plugin: PluginConfig;
  onSave?: () => void;
}

// Build Zod schema from plugin config schema
function buildSchema(sections: ConfigSection[]) {
  const shape: Record<string, z.ZodTypeAny> = {};

  for (const section of sections) {
    for (const field of section.fields) {
      let fieldSchema: z.ZodTypeAny;

      switch (field.fieldType) {
        case "boolean":
          fieldSchema = z.boolean();
          break;
        case "integer": {
          let numSchema = z.number().int();
          // Check for both undefined and null
          if (field.validation?.minValue != null) {
            numSchema = numSchema.min(field.validation.minValue);
          }
          if (field.validation?.maxValue != null) {
            numSchema = numSchema.max(field.validation.maxValue);
          }
          // Allow null for optional integer fields
          fieldSchema = z.union([numSchema, z.null()]);
          break;
        }
        case "float": {
          let floatSchema = z.number();
          if (field.validation?.minValue != null) {
            floatSchema = floatSchema.min(field.validation.minValue);
          }
          if (field.validation?.maxValue != null) {
            floatSchema = floatSchema.max(field.validation.maxValue);
          }
          // Allow null for optional float fields
          fieldSchema = z.union([floatSchema, z.null()]);
          break;
        }
        case "multiselect":
          fieldSchema = z.array(z.union([z.string(), z.number()]));
          break;
        default: {
          let strSchema = z.string();
          // Check for both undefined and null
          if (field.validation?.minLength != null) {
            strSchema = strSchema.min(field.validation.minLength);
          }
          if (field.validation?.maxLength != null) {
            strSchema = strSchema.max(field.validation.maxLength);
          }
          if (field.validation?.pattern) {
            strSchema = strSchema.regex(
              new RegExp(field.validation.pattern),
              field.validation.patternError || "Invalid format"
            );
          }
          // Allow null for optional string fields
          fieldSchema = z.union([strSchema, z.null()]);
          break;
        }
      }

      shape[field.key] = fieldSchema.optional();
    }
  }

  return z.object(shape);
}

// Build default values from config schema
function buildDefaults(sections: ConfigSection[], currentConfig: Record<string, unknown>) {
  const defaults: Record<string, unknown> = {};

  for (const section of sections) {
    for (const field of section.fields) {
      defaults[field.key] = currentConfig[field.key] ?? field.defaultValue;
    }
  }

  return defaults;
}

export function PluginSettingsPanel({ plugin, onSave }: PluginSettingsPanelProps) {
  const updatePluginConfig = useUpdatePluginConfig();
  const togglePlugin = useTogglePlugin();
  
  // Migration confirmation dialog state
  const [migrationDialog, setMigrationDialog] = useState<{
    open: boolean;
    pendingData: Record<string, unknown> | null;
    migrationCheck: RdnChangeCheckResponse | null;
  }>({
    open: false,
    pendingData: null,
    migrationCheck: null,
  });

  // Use sections (from API) - handle empty array safely
  const sections = plugin.sections || [];
  
  const defaultValues = buildDefaults(sections, plugin.config);
  const schema = buildSchema(sections);

  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues,
  });

  // Reset form when plugin changes
  useEffect(() => {
    form.reset(buildDefaults(sections, plugin.config));
  }, [plugin.name]);

  const onSubmit = async (data: Record<string, unknown>, confirmed = false, migrateEntries = true) => {
    const result = await updatePluginConfig.mutateAsync({
      name: plugin.name,
      data: { 
        config: data,
        confirmed,
        migrateEntries,
      },
    });
    
    // Check if migration confirmation is required
    if (result.requiresConfirmation && result.migrationCheck) {
      setMigrationDialog({
        open: true,
        pendingData: data,
        migrationCheck: result.migrationCheck,
      });
      return;
    }
    
    // Success - close dialog if open and call onSave
    setMigrationDialog({ open: false, pendingData: null, migrationCheck: null });
    onSave?.();
  };
  
  const handleMigrationConfirm = async (migrate: boolean) => {
    if (migrationDialog.pendingData) {
      try {
        // Resubmit with confirmation
        await onSubmit(migrationDialog.pendingData, true, migrate);
      } catch (error) {
        // Error is handled by the hook's onError
        // Close the dialog anyway
        setMigrationDialog({ open: false, pendingData: null, migrationCheck: null });
      }
    }
  };
  
  const handleMigrationCancel = () => {
    setMigrationDialog({ open: false, pendingData: null, migrationCheck: null });
  };

  const handleReset = () => {
    form.reset(defaultValues);
  };

  const handleResetToDefaults = () => {
    const defaults: Record<string, unknown> = {};
    for (const section of sections) {
      for (const field of section.fields) {
        defaults[field.key] = field.defaultValue;
      }
    }
    form.reset(defaults);
  };

  const handleToggleEnabled = () => {
    togglePlugin.mutate(plugin.name, !plugin.enabled);
  };

  const isDirty = form.formState.isDirty;
  const isPending = updatePluginConfig.isPending || togglePlugin.isPending;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2">
              {plugin.name}
              <Badge variant={plugin.enabled ? "default" : "secondary"}>
                {plugin.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </CardTitle>
            {plugin.description && (
              <CardDescription>{plugin.description}</CardDescription>
            )}
            <div className="text-xs text-muted-foreground">
              Version {plugin.version}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor={`toggle-${plugin.name}`} className="text-sm">
              {plugin.enabled ? "Enabled" : "Disabled"}
            </Label>
            <Switch
              id={`toggle-${plugin.name}`}
              checked={plugin.enabled}
              onCheckedChange={handleToggleEnabled}
              disabled={isPending}
            />
          </div>
        </div>
      </CardHeader>
      
      {plugin.enabled && sections.length > 0 && (
        <CardContent>
          <form onSubmit={form.handleSubmit((data) => onSubmit(data))} className="space-y-4">
            <Accordion type="multiple" defaultValue={sections.map((s) => s.id)}>
              {sections.map((section) => (
                <AccordionItem key={section.id} value={section.id}>
                  <AccordionTrigger>
                    <div className="flex flex-col items-start">
                      <span>{section.label}</span>
                      {section.description && (
                        <span className="text-xs text-muted-foreground font-normal">
                          {section.description}
                        </span>
                      )}
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-6 pt-4">
                      {section.fields.map((field) => (
                        <ConfigFieldComponent
                          key={field.key}
                          field={field}
                          control={form.control}
                          name={field.key as never}
                          disabled={isPending}
                        />
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>

            <Separator />

            <div className="flex justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={handleResetToDefaults}
                disabled={isPending}
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Reset to Defaults
              </Button>

              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  disabled={!isDirty || isPending}
                >
                  Discard Changes
                </Button>
                <Button
                  type="submit"
                  disabled={!isDirty || isPending}
                >
                  {updatePluginConfig.isPending ? (
                    <>
                      <Save className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      )}
      
      {plugin.enabled && sections.length === 0 && (
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This plugin has no configurable settings.
          </p>
        </CardContent>
      )}
      
      {/* Migration Confirmation Dialog */}
      <AlertDialog open={migrationDialog.open} onOpenChange={(open: boolean) => !open && handleMigrationCancel()}>
        <AlertDialogContent className="max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              RDN Change Requires Migration
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4">
                <p>
                  Changing this RDN setting will affect existing LDAP entries.
                </p>
                
                {migrationDialog.migrationCheck && (
                  <Alert variant="warning" showIcon={false} className="border-amber-200 bg-amber-50 dark:bg-amber-950/20">
                    <Database className="h-4 w-4 text-amber-600" />
                    <AlertTitle className="text-amber-800 dark:text-amber-200">
                      {migrationDialog.migrationCheck.entriesCount} entries will be affected
                    </AlertTitle>
                    <AlertDescription className="text-amber-700 dark:text-amber-300">
                      <div className="mt-2 space-y-1">
                        <p className="text-sm">
                          <strong>From:</strong> {migrationDialog.migrationCheck.oldRdn}
                        </p>
                        <p className="text-sm">
                          <strong>To:</strong> {migrationDialog.migrationCheck.newRdn}
                        </p>
                      </div>
                      {migrationDialog.migrationCheck.entriesDns && 
                       migrationDialog.migrationCheck.entriesDns.length > 0 && (
                        <div className="mt-3">
                          <p className="text-sm font-medium mb-1">Affected entries:</p>
                          <ul className="text-xs space-y-0.5 max-h-32 overflow-y-auto">
                            {migrationDialog.migrationCheck.entriesDns.slice(0, 10).map((dn) => (
                              <li key={dn} className="font-mono truncate">{dn}</li>
                            ))}
                            {migrationDialog.migrationCheck.entriesDns.length > 10 && (
                              <li className="text-muted-foreground">
                                ... and {migrationDialog.migrationCheck.entriesDns.length - 10} more
                              </li>
                            )}
                          </ul>
                        </div>
                      )}
                    </AlertDescription>
                  </Alert>
                )}
                
                <p className="text-sm text-muted-foreground">
                  Choose how to proceed:
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex-col sm:flex-row gap-2">
            <AlertDialogCancel onClick={handleMigrationCancel}>
              Cancel
            </AlertDialogCancel>
            <Button
              variant="outline"
              onClick={() => handleMigrationConfirm(false)}
              disabled={updatePluginConfig.isPending}
            >
              {updatePluginConfig.isPending ? "Saving..." : "Change Setting Only"}
            </Button>
            <Button
              onClick={() => handleMigrationConfirm(true)}
              disabled={updatePluginConfig.isPending}
            >
              {updatePluginConfig.isPending ? "Migrating..." : "Migrate Entries"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
