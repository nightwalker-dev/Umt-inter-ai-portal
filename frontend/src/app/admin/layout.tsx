'use client'

import { useRouter, usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [isAuthorized, setIsAuthorized] = useState(false)

  useEffect(() => {
    // Skip checks for login and first-login pages to prevent loops
    if (pathname === '/admin/login' || pathname === '/admin/first-login') {
      setIsAuthorized(true)
      return
    }

    const checkAuth = async () => {
      const token = document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]
      if (!token) {
        router.push('/admin/login')
        return
      }

      try {
        // We hit an endpoint that requires the guarded user (e.g. teams) to see if we hit the password lock
        const res = await fetch('http://localhost:8000/api/teams', {
          headers: { 'Authorization': `Bearer ${token}` }
        })

        if (res.status === 403) {
          const data = await res.json()
          if (data.detail === "Must change password first") {
            router.push('/admin/first-login')
            return
          }
        }

        setIsAuthorized(true)
      } catch (err) {
        console.error("Auth check failed", err)
        // If network fails, let them see the page but API calls inside will fail
        setIsAuthorized(true)
      }
    }

    checkAuth()
  }, [pathname, router])

  if (!isAuthorized) {
    return <div className="p-8 text-black bg-white min-h-screen">Loading...</div>
  }

  return (
    <div className="flex min-h-screen bg-white text-black">
      {/* Sidebar for authorized users (not login/first-login) */}
      {pathname !== '/admin/login' && pathname !== '/admin/first-login' && (
        <div className="w-64 bg-gray-100 p-4 border-r">
          <h2 className="font-bold text-xl mb-6">Club Portal</h2>
                    <nav className="space-y-2">
            <a href="/admin" className="block p-2 hover:bg-gray-200 rounded">Dashboard</a>
            <a href="/admin/users" className="block p-2 hover:bg-gray-200 rounded">Users</a>
            <a href="/admin/teams" className="block p-2 hover:bg-gray-200 rounded">Teams</a>
            <a href="/admin/timetable" className="block p-2 hover:bg-gray-200 rounded">My Timetable</a>
            <a href="/admin/availability" className="block p-2 hover:bg-gray-200 rounded">Availability</a>
            <a href="/admin/tasks" className="block p-2 hover:bg-gray-200 rounded">Tasks</a>
            <a href="/admin/events" className="block p-2 hover:bg-gray-200 rounded">Events</a>
            <a href="/admin/review" className="block p-2 hover:bg-gray-200 rounded text-blue-600 font-bold">Review Queue</a>
            <a href="/admin/activity" className="block p-2 hover:bg-gray-200 rounded text-red-600 font-bold">Activity Log</a>
          </nav>
        </div>
      )}
      <div className="flex-1">
        {children}
      </div>
    </div>
  )
}
