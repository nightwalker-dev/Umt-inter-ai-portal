'use client'

import { useState, useEffect } from 'react'

export default function UsersPage() {
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchUsers = async () => {
      const token = document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]
      try {
        const res = await fetch('http://localhost:8000/api/users', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Failed to fetch users')
        setUsers(data)
      } catch (err: any) {
        setError(err.message)
      }
    }
    fetchUsers()
  }, [])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">User Management</h1>
      {error && <div className="text-red-500 mb-4">{error}</div>}
      <table className="w-full border-collapse border text-black bg-white">
        <thead>
          <tr className="bg-gray-200">
            <th className="border p-2">Name</th>
            <th className="border p-2">Email</th>
            <th className="border p-2">Role</th>
            <th className="border p-2">Active</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u: any) => (
            <tr key={u.id}>
              <td className="border p-2">{u.full_name}</td>
              <td className="border p-2">{u.email}</td>
              <td className="border p-2">{u.role}</td>
              <td className="border p-2">{u.is_active ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
