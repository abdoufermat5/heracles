/**
 * Attribute Rules Editor Component
 *
 * Manages attribute-level allow/deny rules within a policy.
 * Shows existing rules and allows adding/removing them.
 */

import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { LoadingSpinner } from '@/components/common'
import { useAclPolicyAttrRules, useAclAttributeGroups, useCreatePolicyAttrRule, useDeletePolicyAttrRule } from '@/hooks'
import { attrRuleCreateSchema, type AttrRuleCreateFormData } from '@/lib/schemas'
import { AppError } from '@/lib/errors'
import type { AclPolicyAttrRule } from '@/types/acl'

interface AttrRulesEditorProps {
  policyId: string
  readOnly?: boolean
}

export function AttrRulesEditor({ policyId, readOnly = false }: AttrRulesEditorProps) {
  const [showDialog, setShowDialog] = useState(false)

  const { data: rules, isLoading: rulesLoading } = useAclPolicyAttrRules(policyId)
  const { data: attrGroups, isLoading: groupsLoading } = useAclAttributeGroups()
  const createMutation = useCreatePolicyAttrRule(policyId)
  const deleteMutation = useDeletePolicyAttrRule(policyId)

  const form = useForm<AttrRuleCreateFormData>({
    resolver: zodResolver(attrRuleCreateSchema),
    defaultValues: {
      objectType: '',
      action: 'read',
      ruleType: 'allow',
      attrGroups: [],
    },
  })

  const watchedObjectType = form.watch('objectType')

  // Get unique object types from attribute groups
  const objectTypes = [...new Set(attrGroups?.map((g) => g.objectType) ?? [])]

  // Get attribute groups for the selected object type
  const filteredGroups = attrGroups?.filter((g) => g.objectType === watchedObjectType) ?? []

  const handleCreate = async (data: AttrRuleCreateFormData) => {
    try {
      await createMutation.mutateAsync(data)
      toast.success('Attribute rule created')
      setShowDialog(false)
      form.reset()
    } catch (error) {
      AppError.toastError(error, 'Failed to create attribute rule')
    }
  }

  const handleDelete = async (rule: AclPolicyAttrRule) => {
    try {
      await deleteMutation.mutateAsync(rule.id)
      toast.success('Attribute rule deleted')
    } catch (error) {
      AppError.toastError(error, 'Failed to delete attribute rule')
    }
  }

  if (rulesLoading || groupsLoading) {
    return <LoadingSpinner />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold">Attribute Rules</h4>
          <p className="text-xs text-muted-foreground">
            Control which attribute groups are accessible for read/write per object type.
          </p>
        </div>
        {!readOnly && (
          <Dialog open={showDialog} onOpenChange={setShowDialog}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Plus className="mr-2 h-3 w-3" />
                Add Rule
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Attribute Rule</DialogTitle>
                <DialogDescription>
                  Define which attribute groups are allowed or denied for a specific object type and action.
                </DialogDescription>
              </DialogHeader>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(handleCreate)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="objectType"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Object Type</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select object type" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {objectTypes.map((ot) => (
                              <SelectItem key={ot} value={ot}>
                                {ot.charAt(0).toUpperCase() + ot.slice(1)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="action"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Action</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="read">Read</SelectItem>
                              <SelectItem value="write">Write</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="ruleType"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Rule Type</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="allow">Allow</SelectItem>
                              <SelectItem value="deny">Deny</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  {watchedObjectType && filteredGroups.length > 0 && (
                    <FormField
                      control={form.control}
                      name="attrGroups"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Attribute Groups</FormLabel>
                          <div className="space-y-2 rounded-md border p-3">
                            {filteredGroups.map((group) => (
                              <div key={group.groupName} className="flex items-start gap-2">
                                <Checkbox
                                  id={`attr-group-${group.groupName}`}
                                  checked={field.value.includes(group.groupName)}
                                  onCheckedChange={(checked) => {
                                    if (checked) {
                                      field.onChange([...field.value, group.groupName])
                                    } else {
                                      field.onChange(field.value.filter((g) => g !== group.groupName))
                                    }
                                  }}
                                />
                                <div className="grid gap-0.5 leading-none">
                                  <Label htmlFor={`attr-group-${group.groupName}`} className="cursor-pointer text-sm font-medium">
                                    {group.label}
                                  </Label>
                                  <p className="text-xs text-muted-foreground">
                                    {group.attributes.join(', ')}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createMutation.isPending}>
                      Add Rule
                    </Button>
                  </DialogFooter>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {(!rules || rules.length === 0) ? (
        <p className="text-sm text-muted-foreground italic">
          No attribute rules defined. All attributes are accessible by default.
        </p>
      ) : (
        <div className="space-y-2">
          {rules.map((rule) => (
            <Card key={rule.id} className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline">
                    {rule.objectType}
                  </Badge>
                  <Badge variant="secondary">
                    {rule.action}
                  </Badge>
                  <Badge variant={rule.ruleType === 'deny' ? 'destructive' : 'default'}>
                    {rule.ruleType}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {rule.attrGroups.join(', ')}
                  </span>
                </div>
                {!readOnly && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive"
                    onClick={() => handleDelete(rule)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
