/**
 * Restart Needed Alert Component
 * ===============================
 * 
 * A shared component to display alerts when configuration changes require
 * an application restart to take effect.
 * 
 * Usage:
 * ```tsx
 * <RestartNeededAlert 
 *   show={hasRestartRequiredChanges}
 *   changedSettings={['LDAP Base DN', 'Users RDN']}
 *   onDismiss={() => setShowAlert(false)}
 * />
 * ```
 */

import { AlertTriangle, RefreshCw, X, Info } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface RestartNeededAlertProps {
  /**
   * Whether to show the alert
   */
  show: boolean;
  
  /**
   * List of settings that were changed requiring restart
   */
  changedSettings?: string[];
  
  /**
   * Custom message to display (overrides default)
   */
  message?: string;
  
  /**
   * Alert variant
   */
  variant?: 'warning' | 'info';
  
  /**
   * Whether the alert can be dismissed
   */
  dismissible?: boolean;
  
  /**
   * Callback when alert is dismissed
   */
  onDismiss?: () => void;
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

export function RestartNeededAlert({
  show,
  changedSettings = [],
  message,
  variant = 'warning',
  dismissible = true,
  onDismiss,
  className,
}: RestartNeededAlertProps) {
  if (!show) {
    return null;
  }

  const IconComponent = variant === 'warning' ? AlertTriangle : Info;
  
  const defaultMessage = changedSettings.length > 0
    ? `The following settings require an application restart to take effect: ${changedSettings.join(', ')}.`
    : 'Some configuration changes require an application restart to take effect.';

  return (
    <Alert 
      variant={variant === 'warning' ? 'destructive' : 'default'}
      className={cn(
        'relative',
        variant === 'warning' && 'border-amber-500 bg-amber-50 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200 dark:border-amber-800',
        className
      )}
    >
      <IconComponent className={cn(
        'h-4 w-4',
        variant === 'warning' && 'text-amber-600 dark:text-amber-400'
      )} />
      <AlertTitle className="flex items-center gap-2">
        <RefreshCw className="h-4 w-4" />
        Restart Required
      </AlertTitle>
      <AlertDescription className="mt-2">
        {message || defaultMessage}
        {!message && (
          <p className="mt-2 text-sm opacity-80">
            Please restart the Heracles API service for these changes to take effect.
          </p>
        )}
      </AlertDescription>
      
      {dismissible && onDismiss && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 right-2 h-6 w-6 rounded-full"
          onClick={onDismiss}
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Dismiss</span>
        </Button>
      )}
    </Alert>
  );
}

/**
 * Hook to track settings that require restart
 */
export interface RestartTracker {
  /**
   * Settings that have been changed requiring restart
   */
  changedSettings: string[];
  
  /**
   * Whether any restart-required settings have changed
   */
  hasChanges: boolean;
  
  /**
   * Add a setting that was changed
   */
  addChange: (settingLabel: string) => void;
  
  /**
   * Clear all tracked changes
   */
  clearChanges: () => void;
}

import { useState, useCallback } from 'react';

export function useRestartTracker(): RestartTracker {
  const [changedSettings, setChangedSettings] = useState<string[]>([]);
  
  const addChange = useCallback((settingLabel: string) => {
    setChangedSettings(prev => {
      if (prev.includes(settingLabel)) {
        return prev;
      }
      return [...prev, settingLabel];
    });
  }, []);
  
  const clearChanges = useCallback(() => {
    setChangedSettings([]);
  }, []);
  
  return {
    changedSettings,
    hasChanges: changedSettings.length > 0,
    addChange,
    clearChanges,
  };
}

/**
 * Compact banner variant for persistent display
 */
export interface RestartBannerProps {
  show: boolean;
  onDismiss?: () => void;
  className?: string;
}

export function RestartBanner({
  show,
  onDismiss,
  className,
}: RestartBannerProps) {
  if (!show) {
    return null;
  }

  return (
    <div 
      className={cn(
        'flex items-center justify-between gap-4 px-4 py-2',
        'bg-amber-100 dark:bg-amber-900/50 border-b border-amber-300 dark:border-amber-700',
        'text-amber-900 dark:text-amber-100',
        className
      )}
    >
      <div className="flex items-center gap-2">
        <RefreshCw className="h-4 w-4 animate-pulse" />
        <span className="text-sm font-medium">
          Configuration changes pending restart
        </span>
      </div>
      
      {onDismiss && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-amber-700 hover:text-amber-900 hover:bg-amber-200 dark:text-amber-300 dark:hover:text-amber-100 dark:hover:bg-amber-800"
          onClick={onDismiss}
        >
          <X className="h-3 w-3 mr-1" />
          Dismiss
        </Button>
      )}
    </div>
  );
}
