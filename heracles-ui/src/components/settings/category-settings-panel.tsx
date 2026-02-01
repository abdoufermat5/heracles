/**
 * Category Settings Panel
 * =======================
 *
 * Renders settings for a single configuration category.
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
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Save, RotateCcw } from "lucide-react";
import { ConfigFieldComponent } from "./config-field";
import { useUpdateSetting } from "@/hooks/use-config";
import type { ConfigCategory, ConfigSetting } from "@/types/config";

interface CategorySettingsPanelProps {
  category: ConfigCategory;
  onSave?: () => void;
}

// Build Zod schema from settings
function buildSchema(settings: ConfigSetting[]) {
  const shape: Record<string, z.ZodTypeAny> = {};

  for (const setting of settings) {
    let fieldSchema: z.ZodTypeAny;

    switch (setting.fieldType) {
      case "boolean":
        fieldSchema = z.boolean();
        break;
      case "integer": {
        let numSchema = z.number().int();
        // Check for both undefined and null
        if (setting.validation?.minValue != null) {
          numSchema = numSchema.min(setting.validation.minValue);
        }
        if (setting.validation?.maxValue != null) {
          numSchema = numSchema.max(setting.validation.maxValue);
        }
        // Allow null for optional integer fields
        fieldSchema = z.union([numSchema, z.null()]);
        break;
      }
      case "float": {
        let floatSchema = z.number();
        if (setting.validation?.minValue != null) {
          floatSchema = floatSchema.min(setting.validation.minValue);
        }
        if (setting.validation?.maxValue != null) {
          floatSchema = floatSchema.max(setting.validation.maxValue);
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
        if (setting.validation?.minLength != null) {
          strSchema = strSchema.min(setting.validation.minLength);
        }
        if (setting.validation?.maxLength != null) {
          strSchema = strSchema.max(setting.validation.maxLength);
        }
        if (setting.validation?.pattern) {
          strSchema = strSchema.regex(
            new RegExp(setting.validation.pattern),
            "Invalid format"
          );
        }
        // Allow null for optional string fields
        fieldSchema = z.union([strSchema, z.null()]);
        break;
      }
    }

    shape[setting.key] = fieldSchema.optional();
  }

  return z.object(shape);
}

// Convert setting to ConfigField format
function settingToField(setting: ConfigSetting) {
  return {
    key: setting.key,
    label: setting.label || setting.key,
    description: setting.description,
    fieldType: setting.fieldType,
    defaultValue: setting.defaultValue,
    required: false,
    sensitive: setting.sensitive,
    requiresRestart: setting.requiresRestart,
    validation: setting.validation,
    options: setting.options,
  };
}

export function CategorySettingsPanel({ category, onSave }: CategorySettingsPanelProps) {
  const updateSetting = useUpdateSetting();

  // Safely get settings (handle undefined)
  const settings = category.settings || [];

  // Build default values from settings
  const defaultValues = settings.reduce(
    (acc, setting) => ({
      ...acc,
      [setting.key]: setting.value ?? setting.defaultValue,
    }),
    {} as Record<string, unknown>
  );

  const schema = buildSchema(settings);

  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues,
  });

  // Reset form when category changes
  useEffect(() => {
    form.reset(defaultValues);
  }, [category.name]);

  const onSubmit = async (data: Record<string, unknown>) => {
    // Find changed values and update them
    const changes: { key: string; value: unknown }[] = [];

    for (const [key, value] of Object.entries(data)) {
      const setting = settings.find((s) => s.key === key);
      if (setting && value !== setting.value) {
        changes.push({ key, value });
      }
    }

    // Update each changed setting
    for (const change of changes) {
      await updateSetting.mutateAsync({
        category: category.name,
        key: change.key,
        data: { value: change.value },
      });
    }

    onSave?.();
  };

  const handleReset = () => {
    form.reset(defaultValues);
  };

  const handleResetToDefaults = () => {
    const defaults = settings.reduce(
      (acc, setting) => ({
        ...acc,
        [setting.key]: setting.defaultValue,
      }),
      {} as Record<string, unknown>
    );
    form.reset(defaults);
  };

  const isDirty = form.formState.isDirty;

  // Show empty state if no settings
  if (settings.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{category.label}</CardTitle>
          {category.description && (
            <CardDescription>{category.description}</CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">
            No settings available for this category.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{category.label}</CardTitle>
        {category.description && (
          <CardDescription>{category.description}</CardDescription>
        )}
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {settings.map((setting, index) => (
            <div key={setting.key}>
              <ConfigFieldComponent
                field={settingToField(setting)}
                control={form.control}
                name={setting.key as never}
                disabled={updateSetting.isPending}
              />
              {index < settings.length - 1 && <Separator className="mt-6" />}
            </div>
          ))}

          <Separator />

          <div className="flex justify-between">
            <Button
              type="button"
              variant="outline"
              onClick={handleResetToDefaults}
              disabled={updateSetting.isPending}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Reset to Defaults
            </Button>

            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleReset}
                disabled={!isDirty || updateSetting.isPending}
              >
                Discard Changes
              </Button>
              <Button
                type="submit"
                disabled={!isDirty || updateSetting.isPending}
              >
                {updateSetting.isPending ? (
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
    </Card>
  );
}
