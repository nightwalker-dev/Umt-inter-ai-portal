'use client'
import { useState, useEffect } from 'react'

export default function UsersPage() {
  const [users, setUsers] = useState([])
  const [teams, setTeams] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [newUser, setNewUser] = useState({ email: '', full_name: '', role: 'user', team_id: '' })
  const [tempPassword, setTempPassword] = useState('')

  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    fetchUsers()
    fetchTeams()
  }, [])

  const fetchUsers = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/users', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      setUsers(data)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const fetchTeams = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/teams', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      setTeams(data)
    } catch (err: any) {
      console.error(err)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setTempPassword('')
    try {
      const res = await fetch('http://localhost:8000/api/users', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: newUser.email,
            full_name: newUser.full_name,
            role: newUser.role,
            team_id: newUser.team_id || null
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)

      setTempPassword(data.temp_password)
      setSuccess(`User created successfully. Give them this password: ${data.temp_password}`)
      setNewUser({ email: '', full_name: '', role: 'user', team_id: '' })
      fetchUsers()
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-4">User Management</h1>
      {error && <div className="text-red-500 mb-4 bg-red-100 p-2 rounded">{error}</div>}
      {success && <div className="text-green-800 mb-4 bg-green-100 p-2 rounded font-bold">{success}</div>}

      <div className="mb-8 p-4 border rounded bg-gray-50">
        <h2 className="font-bold mb-4">Create New User (Admin Only)</h2>
        <form onSubmit={handleCreate} className="flex gap-4 flex-wrap items-end">
          <div>
            <label className="block text-xs font-bold mb-1">Full Name</label>
            <input required type="text" value={newUser.full_name} onChange={e => setNewUser({...newUser, full_name: e.target.value})} className="border p-2 rounded w-full" />
          </div>
          <div>
            <label className="block text-xs font-bold mb-1">Email</label>
            <input required type="email" value={newUser.email} onChange={e => setNewUser({...newUser, email: e.target.value})} className="border p-2 rounded w-full" />
          </div>
          <div>
            <label className="block text-xs font-bold mb-1">Role</label>
            <select required value={newUser.role} onChange={e => setNewUser({...newUser, role: e.target.value})} className="border p-2 rounded w-full">
              <option value="user">User</option>
              <option value="lead">Lead</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold mb-1">Team (Optional for Admin)</label>
            <select value={newUser.team_id} onChange={e => setNewUser({...newUser, team_id: e.target.value})} className="border p-2 rounded w-full">
              <option value="">No Team</option>
              {teams.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded font-bold h-10">Create</button>
        </form>
      </div>

      <table className="w-full border-collapse border text-sm">
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
              <td className="border p-2 font-bold">{u.role}</td>
              <td className="border p-2">{u.is_active ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
