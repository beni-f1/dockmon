/**
 * User Management Page
 * 
 * Admin-only page for managing users with role-based access control.
 */

import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersApi } from './api'
import { useAuth } from '@/features/auth/AuthContext'
import { Button } from '@/components/ui/button'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { 
  UserPlus, 
  Edit2, 
  Trash2, 
  KeyRound, 
  Shield, 
  ShieldAlert, 
  ShieldCheck,
  Eye 
} from 'lucide-react'
import { toast } from 'sonner'
import { UserModal } from './UserModal'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import type { User, UserRole, PasswordResetResponse } from '@/types/api'

const ROLE_CONFIG: Record<UserRole, { label: string; icon: React.ReactNode; variant: 'default' | 'secondary' | 'outline' }> = {
  admin: { 
    label: 'Administrator', 
    icon: <ShieldCheck className="h-3 w-3" />, 
    variant: 'default' 
  },
  user: { 
    label: 'Standard User', 
    icon: <Shield className="h-3 w-3" />, 
    variant: 'secondary' 
  },
  readonly: { 
    label: 'Read Only', 
    icon: <Eye className="h-3 w-3" />, 
    variant: 'outline' 
  },
}

export function UsersPage() {
  const { user: currentUser, isAdmin } = useAuth()
  const queryClient = useQueryClient()
  
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<User | null>(null)
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState<User | null>(null)
  const [tempPassword, setTempPassword] = useState<string | null>(null)

  // Fetch users
  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled: isAdmin,
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (userId: number) => usersApi.delete(userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('User deleted successfully')
      setDeleteConfirm(null)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete user')
    },
  })

  // Reset password mutation
  const resetPasswordMutation = useMutation({
    mutationFn: (userId: number) => usersApi.resetPassword(userId),
    onSuccess: (data: PasswordResetResponse) => {
      void queryClient.invalidateQueries({ queryKey: ['users'] })
      setTempPassword(data.temporary_password)
      setResetPasswordConfirm(null)
      toast.success('Password reset successfully')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to reset password')
    },
  })

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <ShieldAlert className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-lg font-semibold">Access Denied</h2>
          <p className="text-muted-foreground">You need administrator privileges to manage users.</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-500">
        Failed to load users: {(error as Error).message}
      </div>
    )
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'Never'
    return new Date(dateStr).toLocaleString()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">User Management</h2>
          <p className="text-muted-foreground">
            Manage user accounts and their access levels
          </p>
        </div>
        <Button onClick={() => { setEditingUser(null); setModalOpen(true) }}>
          <UserPlus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Username</TableHead>
              <TableHead>Display Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last Login</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  Loading users...
                </TableCell>
              </TableRow>
            ) : data?.users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No users found
                </TableCell>
              </TableRow>
            ) : (
              data?.users.map((user: User) => {
                const roleConfig = ROLE_CONFIG[user.role]
                const isCurrentUser = user.id === currentUser?.id
                
                return (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">
                      {user.username}
                      {isCurrentUser && (
                        <Badge variant="outline" className="ml-2 text-xs">You</Badge>
                      )}
                    </TableCell>
                    <TableCell>{user.display_name || '-'}</TableCell>
                    <TableCell>
                      <Badge variant={roleConfig.variant} className="gap-1">
                        {roleConfig.icon}
                        {roleConfig.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {user.must_change_password ? (
                        <Badge variant="outline" className="text-yellow-600 border-yellow-600">
                          Password Change Required
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-green-600 border-green-600">
                          Active
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDate(user.last_login)}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDate(user.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => { setEditingUser(user); setModalOpen(true) }}
                          title="Edit user"
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setResetPasswordConfirm(user)}
                          title="Reset password"
                        >
                          <KeyRound className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteConfirm(user)}
                          disabled={isCurrentUser}
                          title={isCurrentUser ? "Cannot delete yourself" : "Delete user"}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create/Edit Modal */}
      <UserModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        user={editingUser}
        onSuccess={() => {
          setModalOpen(false)
          setEditingUser(null)
          void queryClient.invalidateQueries({ queryKey: ['users'] })
        }}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteConfirm !== null}
        onOpenChange={(open: boolean) => !open && setDeleteConfirm(null)}
        title="Delete User"
        description={`Are you sure you want to delete user "${deleteConfirm?.username}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteConfirm && deleteMutation.mutate(deleteConfirm.id)}
      />

      {/* Reset Password Confirmation */}
      <ConfirmDialog
        open={resetPasswordConfirm !== null}
        onOpenChange={(open: boolean) => !open && setResetPasswordConfirm(null)}
        title="Reset Password"
        description={`Reset password for user "${resetPasswordConfirm?.username}"? They will receive a temporary password and be required to change it on next login.`}
        confirmLabel="Reset Password"
        variant="default"
        isLoading={resetPasswordMutation.isPending}
        onConfirm={() => resetPasswordConfirm && resetPasswordMutation.mutate(resetPasswordConfirm.id)}
      />

      {/* Temporary Password Display */}
      <ConfirmDialog
        open={tempPassword !== null}
        onOpenChange={(open: boolean) => !open && setTempPassword(null)}
        title="Temporary Password"
        description={
          <div className="space-y-4">
            <p>The user's password has been reset. Share this temporary password securely:</p>
            <code className="block p-3 bg-muted rounded-md font-mono text-sm select-all">
              {tempPassword}
            </code>
            <p className="text-sm text-muted-foreground">
              The user will be required to change this password on their next login.
            </p>
          </div>
        }
        confirmLabel="Done"
        showCancel={false}
        onConfirm={() => setTempPassword(null)}
      />
    </div>
  )
}
