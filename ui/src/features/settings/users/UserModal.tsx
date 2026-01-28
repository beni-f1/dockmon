/**
 * User Create/Edit Modal
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { usersApi } from './api'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import type { User, UserRole, UserCreate } from '@/types/api'

const createUserSchema = z.object({
  username: z.string()
    .min(3, 'Username must be at least 3 characters')
    .max(50, 'Username must be at most 50 characters')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Username can only contain letters, numbers, underscores, and hyphens'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .max(100, 'Password must be at most 100 characters')
    .optional()
    .or(z.literal('')),
  display_name: z.string().max(100).optional().or(z.literal('')),
  role: z.enum(['admin', 'user', 'readonly']),
})

const editUserSchema = z.object({
  display_name: z.string().max(100).optional().or(z.literal('')),
  role: z.enum(['admin', 'user', 'readonly']),
})

type CreateFormData = z.infer<typeof createUserSchema>
type EditFormData = z.infer<typeof editUserSchema>

interface UserModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
  onSuccess: () => void
}

const ROLE_OPTIONS: { value: UserRole; label: string; description: string }[] = [
  { 
    value: 'admin', 
    label: 'Administrator', 
    description: 'Full access to all features including user management' 
  },
  { 
    value: 'user', 
    label: 'Standard User', 
    description: 'Can manage containers and hosts but not users' 
  },
  { 
    value: 'readonly', 
    label: 'Read Only', 
    description: 'View-only access, cannot make changes' 
  },
]

export function UserModal({ open, onOpenChange, user, onSuccess }: UserModalProps) {
  const isEditing = user !== null

  const createForm = useForm<CreateFormData>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      username: '',
      password: '',
      display_name: '',
      role: 'user',
    },
  })

  const editForm = useForm<EditFormData>({
    resolver: zodResolver(editUserSchema),
    defaultValues: {
      display_name: '',
      role: 'user',
    },
  })

  // Reset form when modal opens/closes or user changes
  useEffect(() => {
    if (open) {
      if (user) {
        editForm.reset({
          display_name: user.display_name || '',
          role: user.role,
        })
      } else {
        createForm.reset({
          username: '',
          password: '',
          display_name: '',
          role: 'user',
        })
      }
    }
  }, [open, user, createForm, editForm])

  const createMutation = useMutation({
    mutationFn: (data: CreateFormData) => {
      const payload: UserCreate = {
        username: data.username,
        role: data.role,
      }
      if (data.password) {
        payload.password = data.password
      }
      if (data.display_name) {
        payload.display_name = data.display_name
      }
      return usersApi.create(payload)
    },
    onSuccess: (createdUser, variables) => {
      if (!variables.password) {
        toast.success(
          `User "${createdUser.username}" created. A temporary password was generated and they will need to change it on first login.`
        )
      } else {
        toast.success(`User "${createdUser.username}" created successfully`)
      }
      onSuccess()
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create user')
    },
  })

  const editMutation = useMutation({
    mutationFn: (data: EditFormData) => usersApi.update(user!.id, {
      display_name: data.display_name || null,
      role: data.role,
    }),
    onSuccess: () => {
      toast.success('User updated successfully')
      onSuccess()
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update user')
    },
  })

  const handleSubmit = isEditing
    ? editForm.handleSubmit((data) => editMutation.mutate(data))
    : createForm.handleSubmit((data) => createMutation.mutate(data))

  const isPending = createMutation.isPending || editMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit User' : 'Create User'}</DialogTitle>
          <DialogDescription>
            {isEditing 
              ? 'Update user details and access level.'
              : 'Create a new user account. Leave password empty to generate a temporary one.'}
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {!isEditing && (
            <>
              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  placeholder="johndoe"
                  {...createForm.register('username')}
                />
                {createForm.formState.errors.username && (
                  <p className="text-sm text-red-500">
                    {createForm.formState.errors.username.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">
                  Password <span className="text-muted-foreground">(optional)</span>
                </Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Leave empty for temporary password"
                  {...createForm.register('password')}
                />
                {createForm.formState.errors.password && (
                  <p className="text-sm text-red-500">
                    {createForm.formState.errors.password.message}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  If left empty, a secure temporary password will be generated and the user will be required to change it on first login.
                </p>
              </div>
            </>
          )}

          <div className="space-y-2">
            <Label htmlFor="display_name">Display Name</Label>
            <Input
              id="display_name"
              placeholder="John Doe"
              {...(isEditing ? editForm.register('display_name') : createForm.register('display_name'))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select
              value={isEditing ? editForm.watch('role') : createForm.watch('role')}
              onValueChange={(value: string) => {
                const roleValue = value as UserRole
                if (isEditing) {
                  editForm.setValue('role', roleValue)
                } else {
                  createForm.setValue('role', roleValue)
                }
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                {ROLE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div className="flex flex-col">
                      <span>{option.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {option.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving...' : isEditing ? 'Update User' : 'Create User'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
