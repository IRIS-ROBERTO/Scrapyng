import { redirect } from 'next/navigation'

export default function Home() {
  // In production this would check for a valid session server-side
  // For now, redirect to login (middleware handles authenticated users)
  redirect('/login')
}
