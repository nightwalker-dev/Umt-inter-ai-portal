'use client'

import { useState, useEffect } from 'react'

export default function TeamsPage() {
  const [teams, setTeams] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchTeams = async () => {
      const token = document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]
      try {
        const res = await fetch('http://localhost:8000/api/teams', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Failed to fetch teams')
        setTeams(data)
      } catch (err: any) {
        setError(err.message)
      }
    }
    fetchTeams()
  }, [])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Teams</h1>
      {error && <div className="text-red-500 mb-4">{error}</div>}
      <ul className="text-black bg-white">
        {teams.map((t: any) => (
          <li key={t.id} className="border p-4 mb-2 rounded">
            <strong>{t.name}</strong>
          </li>
        ))}
      </ul>
    </div>
  )
}
