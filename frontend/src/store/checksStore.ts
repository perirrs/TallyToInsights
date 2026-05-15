import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ChecksStore {
  /** Per-dump check selection. null = all selected. number[] = specific subset. */
  selections: Record<string, number[] | null>
  /** Whether the sidebar is globally collapsed */
  sidebarCollapsed: boolean

  getSelection: (dumpId: string) => number[] | null
  setSelection: (dumpId: string, ids: number[] | null) => void
  setSidebarCollapsed: (v: boolean) => void
}

export const useChecksStore = create<ChecksStore>()(
  persist(
    (set, get) => ({
      selections: {},
      sidebarCollapsed: false,

      getSelection: (dumpId) => {
        const v = get().selections[dumpId]
        return v === undefined ? null : v   // undefined → not yet set → all selected
      },

      setSelection: (dumpId, ids) =>
        set((s) => ({ selections: { ...s.selections, [dumpId]: ids } })),

      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
    }),
    { name: 'tally-checks-selection' },
  ),
)
