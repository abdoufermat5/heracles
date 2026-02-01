/**
 * Config Field Component
 * ======================
 *
 * Dynamic form field renderer based on config field type.
 */

import type { Control, FieldValues, Path } from "react-hook-form";
import { useController } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, RefreshCw, Lock } from "lucide-react";
import type { ConfigField } from "@/types/config";
import { cn } from "@/lib/utils";

interface ConfigFieldProps<T extends FieldValues> {
  field: ConfigField;
  control: Control<T>;
  name: Path<T>;
  disabled?: boolean;
}

export function ConfigFieldComponent<T extends FieldValues>({
  field,
  control,
  name,
  disabled = false,
}: ConfigFieldProps<T>) {
  const {
    field: controllerField,
    fieldState: { error },
  } = useController({
    name,
    control,
  });

  const renderField = () => {
    switch (field.fieldType) {
      case "boolean":
        return (
          <div className="flex items-center gap-2">
            <Switch
              id={name}
              checked={controllerField.value as boolean}
              onCheckedChange={controllerField.onChange}
              disabled={disabled}
            />
            <Label
              htmlFor={name}
              className={cn("cursor-pointer", disabled && "cursor-not-allowed opacity-50")}
            >
              {controllerField.value ? "Enabled" : "Disabled"}
            </Label>
          </div>
        );

      case "integer":
      case "float":
        return (
          <Input
            id={name}
            type="number"
            step={field.fieldType === "float" ? "0.01" : "1"}
            min={field.validation?.minValue}
            max={field.validation?.maxValue}
            value={controllerField.value ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              if (val === "") {
                controllerField.onChange(null);
              } else {
                controllerField.onChange(
                  field.fieldType === "float" ? parseFloat(val) : parseInt(val, 10)
                );
              }
            }}
            disabled={disabled}
            className={cn(error && "border-destructive")}
          />
        );

      case "select":
        return (
          <Select
            value={String(controllerField.value)}
            onValueChange={controllerField.onChange}
            disabled={disabled}
          >
            <SelectTrigger id={name} className={cn(error && "border-destructive")}>
              <SelectValue placeholder="Select an option" />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((option) => (
                <SelectItem key={String(option.value)} value={String(option.value)}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case "multiselect":
        const selectedValues = (controllerField.value as (string | number)[]) || [];
        return (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-1 mb-2 min-h-[32px] p-2 border rounded-md bg-muted/30">
              {selectedValues.length === 0 ? (
                <span className="text-muted-foreground text-sm">None selected</span>
              ) : (
                selectedValues.map((val) => {
                  const option = field.options?.find((o) => String(o.value) === String(val));
                  return (
                    <Badge key={String(val)} variant="secondary" className="text-xs">
                      {option?.label || String(val)}
                    </Badge>
                  );
                })
              )}
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto border rounded-md p-2">
              {field.options?.map((option) => {
                const isSelected = selectedValues.includes(option.value as string | number);
                return (
                  <div key={String(option.value)} className="flex items-center space-x-2">
                    <Checkbox
                      id={`${name}-${option.value}`}
                      checked={isSelected}
                      disabled={disabled}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          controllerField.onChange([...selectedValues, option.value]);
                        } else {
                          controllerField.onChange(
                            selectedValues.filter((v) => v !== option.value)
                          );
                        }
                      }}
                    />
                    <Label
                      htmlFor={`${name}-${option.value}`}
                      className={cn("cursor-pointer text-sm", disabled && "cursor-not-allowed opacity-50")}
                    >
                      {option.label}
                    </Label>
                  </div>
                );
              })}
            </div>
          </div>
        );

      case "password":
        return (
          <Input
            id={name}
            type="password"
            value={controllerField.value ?? ""}
            onChange={controllerField.onChange}
            disabled={disabled}
            className={cn(error && "border-destructive")}
            autoComplete="off"
          />
        );

      case "json":
        return (
          <Textarea
            id={name}
            value={
              typeof controllerField.value === "string"
                ? controllerField.value
                : JSON.stringify(controllerField.value, null, 2)
            }
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                controllerField.onChange(parsed);
              } catch {
                controllerField.onChange(e.target.value);
              }
            }}
            disabled={disabled}
            className={cn("font-mono text-sm", error && "border-destructive")}
            rows={5}
          />
        );

      case "url":
      case "email":
      case "path":
      case "string":
      default:
        return (
          <Input
            id={name}
            type={field.fieldType === "email" ? "email" : "text"}
            value={controllerField.value ?? ""}
            onChange={controllerField.onChange}
            disabled={disabled}
            className={cn(error && "border-destructive")}
            placeholder={field.fieldType === "url" ? "https://..." : undefined}
            minLength={field.validation?.minLength}
            maxLength={field.validation?.maxLength}
          />
        );
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Label htmlFor={name} className={cn(field.required && "after:content-['*'] after:text-destructive after:ml-0.5")}>
          {field.label}
        </Label>
        {field.requiresRestart && (
          <Badge variant="outline" className="text-xs gap-1">
            <RefreshCw className="h-3 w-3" />
            Restart
          </Badge>
        )}
        {field.sensitive && (
          <Badge variant="outline" className="text-xs gap-1">
            <Lock className="h-3 w-3" />
            Sensitive
          </Badge>
        )}
      </div>
      
      {field.description && (
        <p className="text-sm text-muted-foreground">{field.description}</p>
      )}
      
      {renderField()}
      
      {error && (
        <p className="flex items-center gap-1 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error.message}
        </p>
      )}
    </div>
  );
}
