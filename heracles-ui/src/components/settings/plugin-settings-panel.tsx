/**
 * Plugin Settings Panel
 * =====================
 *
 * Renders settings for a single plugin configuration.
 */

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useEffect } from "react";
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
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Save, RotateCcw } from "lucide-react";
import { ConfigFieldComponent } from "./config-field";
import { useUpdatePluginConfig, useTogglePlugin } from "@/hooks/use-config";
import type { PluginConfig, ConfigSection } from "@/types/config";

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

  const onSubmit = async (data: Record<string, unknown>) => {
    await updatePluginConfig.mutateAsync({
      name: plugin.name,
      data: { config: data },
    });
    onSave?.();
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
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
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
    </Card>
  );
}
