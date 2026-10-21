import { createClient } from '@supabase/supabase-js'
import { Suspense } from 'react'

// Allow blocking route for runtime data fetching
export const instant = false

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

async function getSummary() {
  const { data, error } = await supabase.from('budget_summary').select('*')
  if (error) throw error
  return data
}

async function BudgetTable() {
  const summary = await getSummary()

  return (
    <table className="w-full border-collapse border border-gray-300">
      <thead>
        <tr className="bg-gray-100">
          <th className="border p-2 text-left">Groupe Politique</th>
          <th className="border p-2 text-right">Total Budgetary Impact (€)</th>
        </tr>
      </thead>
      <tbody>
        {summary?.map((row) => (
          <tr key={row.groupe_politique}>
            <td className="border p-2">{row.groupe_politique}</td>
            <td className="border p-2 text-right font-mono">
              {Number(row.total_impact).toLocaleString()} €
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function Dashboard() {
  return (
    <main className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">National Assembly Budgetary Impact Dashboard</h1>
      <Suspense fallback={<div className="text-gray-500">Loading budget data...</div>}>
        <BudgetTable />
      </Suspense>
    </main>
  )
}
