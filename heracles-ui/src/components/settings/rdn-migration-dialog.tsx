/**
 * RDN Migration Confirmation Dialog
 * ==================================
 *
 * Dialog shown when a user attempts to change an RDN setting that would affect existing entries.
 * Warns about migration implications and allows the user to confirm or cancel.
 */

import { AlertTriangle, Database, FolderSync, Move } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import type { RdnChangeCheckResponse } from "@/types/config";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface RdnMigrationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  migrationCheck: RdnChangeCheckResponse;
  onConfirm: (migrate: boolean) => void;
  isLoading?: boolean;
}

export function RdnMigrationDialog({
  open,
  onOpenChange,
  migrationCheck,
  onConfirm,
  isLoading = false,
}: RdnMigrationDialogProps) {
  const [migrateEntries, setMigrateEntries] = useState(true);

  const handleConfirm = () => {
    onConfirm(migrateEntries);
  };

  const getModeLabel = (mode: string) => {
    switch (mode) {
      case "modrdn":
        return "ModRDN (recommended)";
      case "copy_delete":
        return "Copy & Delete";
      case "leave_orphaned":
        return "Leave in place";
      default:
        return mode;
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            RDN Change Affects Existing Entries
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p>
                Changing the RDN from{" "}
                <Badge variant="outline" className="font-mono">
                  {migrationCheck.oldRdn}
                </Badge>{" "}
                to{" "}
                <Badge variant="outline" className="font-mono">
                  {migrationCheck.newRdn}
                </Badge>{" "}
                will affect <strong>{migrationCheck.entriesCount}</strong>{" "}
                existing {migrationCheck.entriesCount === 1 ? "entry" : "entries"}.
              </p>

              {/* Warnings */}
              {migrationCheck.warnings.length > 0 && (
                <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-950">
                  <h4 className="mb-2 font-medium text-yellow-800 dark:text-yellow-200">
                    Warnings
                  </h4>
                  <ul className="list-inside list-disc space-y-1 text-sm text-yellow-700 dark:text-yellow-300">
                    {migrationCheck.warnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Affected entries preview */}
              {migrationCheck.entriesDns.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Affected Entries</h4>
                  <div className="h-32 overflow-auto rounded-md border p-2">
                    <ul className="space-y-1 font-mono text-xs text-muted-foreground">
                      {migrationCheck.entriesDns.map((dn, index) => (
                        <li key={index} className="truncate">
                          {dn}
                        </li>
                      ))}
                      {migrationCheck.entriesCount >
                        migrationCheck.entriesDns.length && (
                        <li className="text-muted-foreground italic">
                          ... and{" "}
                          {migrationCheck.entriesCount -
                            migrationCheck.entriesDns.length}{" "}
                          more
                        </li>
                      )}
                    </ul>
                  </div>
                </div>
              )}

              <Separator />

              {/* Migration options using simple clickable divs */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium">What would you like to do?</h4>
                <div className="space-y-2">
                  {/* Migrate option */}
                  <div
                    onClick={() => setMigrateEntries(true)}
                    className={cn(
                      "flex cursor-pointer items-start space-x-3 rounded-md border p-3 hover:bg-muted/50",
                      migrateEntries && "border-primary bg-primary/5"
                    )}
                  >
                    <div className={cn(
                      "mt-0.5 h-4 w-4 rounded-full border-2",
                      migrateEntries ? "border-primary bg-primary" : "border-muted-foreground"
                    )}>
                      {migrateEntries && (
                        <div className="m-0.5 h-2 w-2 rounded-full bg-white" />
                      )}
                    </div>
                    <Label className="flex-1 cursor-pointer">
                      <div className="flex items-center gap-2">
                        <Move className="h-4 w-4 text-blue-500" />
                        <span className="font-medium">Migrate entries</span>
                        {migrationCheck.supportsModrdn && (
                          <Badge variant="secondary" className="text-xs">
                            Recommended
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        Move all entries to the new location using{" "}
                        {getModeLabel(migrationCheck.recommendedMode)}.
                        {!migrationCheck.supportsModrdn && (
                          <span className="block text-yellow-600 dark:text-yellow-400">
                            Note: Your LDAP server may not support native
                            modRDN, so entries will be copied then deleted.
                          </span>
                        )}
                      </p>
                    </Label>
                  </div>

                  {/* Leave in place option */}
                  <div
                    onClick={() => setMigrateEntries(false)}
                    className={cn(
                      "flex cursor-pointer items-start space-x-3 rounded-md border p-3 hover:bg-muted/50",
                      !migrateEntries && "border-primary bg-primary/5"
                    )}
                  >
                    <div className={cn(
                      "mt-0.5 h-4 w-4 rounded-full border-2",
                      !migrateEntries ? "border-primary bg-primary" : "border-muted-foreground"
                    )}>
                      {!migrateEntries && (
                        <div className="m-0.5 h-2 w-2 rounded-full bg-white" />
                      )}
                    </div>
                    <Label className="flex-1 cursor-pointer">
                      <div className="flex items-center gap-2">
                        <Database className="h-4 w-4 text-gray-500" />
                        <span className="font-medium">Leave entries in place</span>
                        <Badge variant="outline" className="text-xs text-yellow-600">
                          Not recommended
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        Keep entries in the old location. They will become
                        orphaned and no longer be visible in the application.
                        You can migrate them later manually.
                      </p>
                    </Label>
                  </div>
                </div>
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isLoading}>
            {isLoading ? (
              <>
                <FolderSync className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Move className="mr-2 h-4 w-4" />
                {migrateEntries ? "Confirm & Migrate" : "Confirm Without Migration"}
              </>
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
