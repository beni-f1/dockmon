/**
 * User Management API
 * 
 * Admin-only endpoints for managing users with role-based access control.
 */

import { apiClient } from '@/lib/api/client'
import type { 
  User, 
  UserCreate, 
  UserUpdate, 
  UserListResponse, 
  PasswordResetResponse,
  AvailableRolesResponse 
} from '@/types/api'

const BASE_PATH = '/v2/users'

export const usersApi = {
  /**
   * List all users (admin only)
   */
  async list(): Promise<UserListResponse> {
    return apiClient.get<UserListResponse>(BASE_PATH)
  },

  /**
   * Get a specific user by ID (admin only)
   */
  async get(userId: number): Promise<User> {
    return apiClient.get<User>(`${BASE_PATH}/${userId}`)
  },

  /**
   * Create a new user (admin only)
   */
  async create(data: UserCreate): Promise<User> {
    return apiClient.post<User>(BASE_PATH, data)
  },

  /**
   * Update a user (admin only)
   */
  async update(userId: number, data: UserUpdate): Promise<User> {
    return apiClient.patch<User>(`${BASE_PATH}/${userId}`, data)
  },

  /**
   * Delete a user (admin only)
   */
  async delete(userId: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`${BASE_PATH}/${userId}`)
  },

  /**
   * Reset a user's password (admin only)
   */
  async resetPassword(userId: number): Promise<PasswordResetResponse> {
    return apiClient.post<PasswordResetResponse>(`${BASE_PATH}/${userId}/reset-password`)
  },

  /**
   * Get available roles with descriptions
   */
  async getAvailableRoles(): Promise<AvailableRolesResponse> {
    return apiClient.get<AvailableRolesResponse>(`${BASE_PATH}/roles/available`)
  },
}
