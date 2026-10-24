'use client'
import { useState, useEffect } from 'react'

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null)
  const [error, setError] = useState('')

  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/me', {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail)
        setProfile(data.profile)
      } catch (err: any) {
        setError(err.message)
      }
    }
    fetchProfile()
  }, [])

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-4">My Profile</h1>
      {error && <div className="text-red-500 mb-4">{error}</div>}

      {profile && (
        <div className="border p-6 rounded shadow max-w-md">
          <p><strong>Name:</strong> {profile.full_name}</p>
          <p><strong>Email:</strong> {profile.email}</p>
          <p><strong>Role:</strong> <span className="uppercase font-bold">{profile.role}</span></p>

          <div className="mt-8 border-t pt-4">
             <p className="text-sm text-gray-500">To change your password or name, please contact your Admin.</p>
          </div>
        </div>
      )}
    </div>
  )
}
