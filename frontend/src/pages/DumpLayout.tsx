import { useParams } from 'react-router-dom'
import { Outlet } from 'react-router-dom'
import ChecksSidebar from '../components/ChecksSidebar'

/**
 * Shared layout for all /dumps/:dumpId/* routes.
 * Renders the persistent Checks sidebar on the left, with the page content on the right.
 * The sidebar selection is saved per-dump in localStorage via checksStore.
 */
export default function DumpLayout() {
  const { dumpId } = useParams<{ dumpId: string }>()

  return (
    <div className="flex" style={{ minHeight: '100vh' }}>
      <ChecksSidebar dumpId={dumpId!} />
      <div className="flex-1 min-w-0 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  )
}
