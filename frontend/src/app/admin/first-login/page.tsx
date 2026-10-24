'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function FirstLoginPage() {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    const token = document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

    try {
      const res = await fetch('http://localhost:8000/api/auth/first-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ new_password: password })
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || "Failed to update password")
      }

      router.push('/admin')
      router.refresh()
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm border p-6 rounded shadow">
        <h1 className="text-xl mb-4 font-bold">Set New Password</h1>
        <p className="text-sm mb-4">You must change your password on first login.</p>
        {error && <div className="text-red-500 mb-4 text-sm">{error}</div>}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">New Password (min 12 chars)</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full p-2 border text-black rounded"
            minLength={12}
            required
          />
        </div>
        <div className="mb-6">
          <label className="block text-sm font-medium mb-1">Confirm Password</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={e => setConfirmPassword(e.target.value)}
            className="w-full p-2 border text-black rounded"
            minLength={12}
            required
          />
        </div>
        <button type="submit" className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
          Update Password
        </button>
      </form>
    </div>
  )
}
